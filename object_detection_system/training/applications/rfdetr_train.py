import csv
import json
import os
import platform
import tempfile
import threading
from argparse import Namespace
from pathlib import Path

import yaml
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from .rf_detr_training_config import load_aug_config
from .rfdetr_native import create_model, prepare_rfdetr_dataset, training_kwargs_from_args


def _read_dataset_yaml(data_yaml):
    with open(data_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    dataset_root = Path(data.get("path") or Path(data_yaml).parent)
    if not dataset_root.is_absolute():
        dataset_root = Path(data_yaml).parent / dataset_root
    names = data.get("names") or {}
    if isinstance(names, dict):
        class_names = [name for _, name in sorted(names.items(), key=lambda item: int(item[0]))]
    else:
        class_names = list(names)
    return dataset_root, class_names


def _find_checkpoint(output_dir):
    output_dir = Path(output_dir)
    preferred = [
        output_dir / "checkpoint_best_regular.pth",
        output_dir / "checkpoint_best_ema.pth",
        output_dir / "checkpoint_best_total.pth",
        output_dir / "checkpoint.pth",
    ]
    for path in preferred:
        if path.exists():
            return path
    candidates = sorted(output_dir.rglob("*.pth"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else output_dir / "checkpoint_best_regular.pth"


def _read_metrics(output_dir):
    metrics_path = Path(output_dir) / "metrics.csv"
    if not metrics_path.exists():
        return {}
    with metrics_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    latest = rows[-1]
    metrics = {}
    for key, value in latest.items():
        if value in (None, ""):
            continue
        try:
            metrics[key] = float(value)
        except ValueError:
            metrics[key] = value
    return metrics


def _format_training_metrics(row):
    metrics = {}
    for key, value in row.items():
        if key in ("epoch", "Epoch", "epochs"):
            continue
        if key in ("", None) or value in (None, ""):
            continue
        try:
            metrics[key] = float(f"{float(value):.4f}")
        except (TypeError, ValueError):
            continue
    return metrics


def _row_epoch(row, fallback_epoch):
    for key in ("epoch", "Epoch", "epochs"):
        value = row.get(key)
        if value not in (None, ""):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                pass
    return fallback_epoch


def _send_training_metrics(epoch, total_epochs, metrics):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "rfdetr_training",
        {
            "type": "send_metrics",
            "epoch": epoch,
            "total_epochs": total_epochs,
            "metrics": metrics,
        },
    )


def _monitor_metrics_file(output_dir, total_epochs, stop_event, poll_interval=1.0):
    metrics_path = Path(output_dir) / "metrics.csv"
    sent_rows = 0
    while not stop_event.is_set():
        sent_rows = _send_new_metric_rows(metrics_path, total_epochs, sent_rows)
        stop_event.wait(poll_interval)
    _send_new_metric_rows(metrics_path, total_epochs, sent_rows)


def _send_new_metric_rows(metrics_path, total_epochs, sent_rows=0):
    if not metrics_path.exists():
        return sent_rows
    try:
        with metrics_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except (OSError, csv.Error):
        return sent_rows
    for index, row in enumerate(rows[sent_rows:], start=sent_rows + 1):
        metrics = _format_training_metrics(row)
        if not metrics:
            continue
        epoch = _row_epoch(row, index)
        _send_training_metrics(epoch, total_epochs, metrics)
    return len(rows)


def _default_accelerator():
    # RF-DETR can hit unsupported MPS ops on macOS; prefer CPU unless explicitly overridden.
    return "auto" if platform.system() != "Darwin" else "cpu"


def _configure_training_cache_dirs():
    cache_root = Path(tempfile.gettempdir()) / "object_detection_system_rfdetr_cache"
    matplotlib_cache = cache_root / "matplotlib"
    xdg_cache = cache_root / "xdg"
    matplotlib_cache.mkdir(parents=True, exist_ok=True)
    xdg_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache))
    os.environ.setdefault("XDG_CACHE_HOME", str(xdg_cache))


def _build_args(model_name, dataset_root, class_names, epochs, resolution, batch_size, output_dir, other_params):
    params = dict(other_params)
    resolution = params.pop("resolution", resolution)
    resolution = int(resolution) if resolution not in (None, "") else None
    batch_size = int(params.pop("batch_size", params.pop("batch", batch_size)))
    num_workers = int(params.pop("num_workers", params.pop("workers", 0)))
    grad_accum_steps = int(params.pop("grad_accum_steps", params.pop("grad_accumulation_steps", 4)))
    aug_config = load_aug_config(params.pop("aug_config", params.pop("augmentation", None)))
    num_queries = params.pop("num_queries", None)
    num_select = params.pop("num_select", None)
    return Namespace(
        dataset_dir=None,
        coco_dir=str(dataset_root / "annotations"),
        images_root=str(dataset_root / "images"),
        model_name=model_name or "Roboflow/rf-detr-large",
        output_dir=str(output_dir),
        pretrain_weights=params.pop("pretrain_weights", None),
        resume=params.pop("resume", None),
        batch_size=batch_size,
        grad_accum_steps=grad_accum_steps,
        lr=float(params.pop("lr", 1.0e-4)),
        lr_encoder=float(params.pop("lr_encoder", 1.5e-4)),
        weight_decay=float(params.pop("weight_decay", 1.0e-4)),
        epochs=int(epochs),
        resolution=resolution,
        accelerator=params.pop("accelerator", _default_accelerator()),
        seed=params.pop("seed", 42),
        gradient_checkpointing=bool(params.pop("gradient_checkpointing", False)),
        use_ema=bool(params.pop("use_ema", True)),
        drop_path=float(params.pop("drop_path", 0.0)),
        checkpoint_interval=int(params.pop("checkpoint_interval", 10)),
        resume_path=None,
        tensorboard=bool(params.pop("tensorboard", False)),
        wandb=bool(params.pop("wandb", False)),
        wandb_project=params.pop("wandb_project", params.pop("project", None)),
        run_name=params.pop("run_name", params.pop("run", None)),
        max_detections=int(params.pop("max_detections", params.pop("eval_max_dets", 500))),
        eval_interval=int(params.pop("eval_interval", 1)),
        log_per_class_metrics=bool(params.pop("log_per_class_metrics", True)),
        progress_bar=params.pop("progress_bar", None),
        lr_scheduler=params.pop("lr_scheduler", "cosine"),
        lr_min_factor=float(params.pop("lr_min_factor", 0.0)),
        warmup_epochs=float(params.pop("warmup_epochs", 0.0)),
        compute_val_loss=bool(params.pop("compute_val_loss", True)),
        compute_test_loss=bool(params.pop("compute_test_loss", True)),
        fp16_eval=bool(params.pop("fp16_eval", False)),
        pin_memory=params.pop("pin_memory", None),
        persistent_workers=params.pop("persistent_workers", None),
        prefetch_factor=params.pop("prefetch_factor", None),
        num_workers=num_workers,
        early_stopping=bool(params.pop("early_stopping", False)),
        early_stopping_patience=int(params.pop("early_stopping_patience", 10)),
        early_stopping_min_delta=float(params.pop("early_stopping_min_delta", 0.001)),
        early_stopping_use_ema=bool(params.pop("early_stopping_use_ema", False)),
        aug_config=aug_config,
        num_queries=num_queries,
        num_select=num_select,
        num_classes=len(class_names),
        extra_params=params,
    )


def _write_detect_yaml(output_dir, best_model_path, model_name, class_names, num_queries, num_select):
    detect_yaml_path = Path(output_dir) / "detect.yaml"
    data = {
        "RF_DETR": {
            "model_path": str(best_model_path),
            "model_name": model_name or "Roboflow/rf-detr-large",
            "num_queries": num_queries,
            "num_classes": len(class_names),
            "num_select": num_select,
            "class_names": class_names,
            "detect_config": {
                "conf": 0.45,
                "verbose": False,
            },
        },
        "image_size": {
            "type": "HD1080p",
        },
    }
    with detect_yaml_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return detect_yaml_path


def run_rfdetr_training(model_name, data_yaml, epochs, resolution, batch_size, device, save_dir=None, **other_params):
    """Train RF-DETR using RF-DETR parameter names."""
    _configure_training_cache_dirs()
    dataset_root, class_names = _read_dataset_yaml(data_yaml)
    if not class_names:
        raise ValueError("データセットYAMLにクラス名がありません")

    output_dir = Path(settings.PROJECTS_DIR) / save_dir if save_dir else Path(settings.PROJECT_ROOT) / "rf_detr_finetuned"
    output_dir.mkdir(parents=True, exist_ok=True)

    args = _build_args(model_name, dataset_root, class_names, epochs, resolution, batch_size, output_dir, other_params)
    if args.extra_params:
        unknown = ", ".join(sorted(args.extra_params.keys()))
        raise ValueError(f"RF-DETR training parameters are unsupported: {unknown}")

    args.dataset_dir = prepare_rfdetr_dataset(
        coco_dir=args.coco_dir,
        images_root=args.images_root,
        work_dir=Path(args.output_dir) / "_rfdetr_dataset",
    )

    pretrain_weights = args.pretrain_weights
    if args.resume and Path(args.resume).exists():
        pretrain_weights = None
    elif pretrain_weights is None and args.model_name and Path(str(args.model_name)).exists():
        pretrain_weights = args.model_name

    model = create_model(
        model_name=args.model_name,
        pretrain_weights=pretrain_weights,
        num_classes=args.num_classes,
        num_queries=args.num_queries,
        num_select=args.num_select,
    )
    kwargs = training_kwargs_from_args(args)
    print(f"Training RF-DETR model: {args.model_name} on {args.dataset_dir}")
    stop_metrics_monitor = threading.Event()
    metrics_monitor = threading.Thread(
        target=_monitor_metrics_file,
        args=(output_dir, args.epochs, stop_metrics_monitor),
        daemon=True,
    )
    metrics_monitor.start()
    try:
        model.train(**kwargs)
    finally:
        stop_metrics_monitor.set()
        metrics_monitor.join(timeout=5)

    best_model_path = _find_checkpoint(output_dir)
    config_yaml_path = _write_detect_yaml(
        output_dir=output_dir,
        best_model_path=best_model_path,
        model_name=args.model_name,
        class_names=class_names,
        num_queries=args.num_queries,
        num_select=args.num_select,
    )
    all_params = dict(kwargs)
    all_params.update({
        "model_name": args.model_name,
        "coco_dir": args.coco_dir,
        "images_root": args.images_root,
        "output_dir": str(output_dir),
    })
    return _read_metrics(output_dir), str(best_model_path), str(config_yaml_path), all_params
