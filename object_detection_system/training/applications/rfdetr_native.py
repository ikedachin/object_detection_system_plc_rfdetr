import json
import os
import shutil
from pathlib import Path


MODEL_CLASS_NAMES = {
    "nano": "RFDETRNano",
    "n": "RFDETRNano",
    "rfdetr-nano": "RFDETRNano",
    "small": "RFDETRSmall",
    "s": "RFDETRSmall",
    "rfdetr-small": "RFDETRSmall",
    "medium": "RFDETRMedium",
    "m": "RFDETRMedium",
    "rfdetr-medium": "RFDETRMedium",
    "base": "RFDETRBase",
    "b": "RFDETRBase",
    "rfdetr-base": "RFDETRBase",
    "large": "RFDETRLarge",
    "l": "RFDETRLarge",
    "rfdetr-large": "RFDETRLarge",
    "roboflow/rf-detr-large": "RFDETRLarge",
}


def require_rfdetr():
    try:
        import rfdetr
    except ImportError as exc:
        raise ImportError(
            "rfdetr is not installed. Install it with `pip install rfdetr` "
            "or `uv pip install rfdetr` before running this script."
        ) from exc
    return rfdetr


def resolve_model_class(model_name):
    rfdetr = require_rfdetr()
    key = (model_name or "rfdetr-large").lower()
    if os.path.exists(model_name or ""):
        key = "rfdetr-large"
    key = key.replace("rf-detr", "rfdetr")
    class_name = MODEL_CLASS_NAMES.get(key, "RFDETRLarge")
    try:
        return getattr(rfdetr, class_name)
    except AttributeError as exc:
        raise RuntimeError(f"Installed rfdetr package does not expose {class_name}") from exc


def create_model(
    model_name="Roboflow/rf-detr-large",
    pretrain_weights=None,
    num_queries=None,
    num_classes=None,
    num_select=None,
):
    model_cls = resolve_model_class(model_name)
    model_kwargs = {}
    if num_queries is not None:
        model_kwargs["num_queries"] = num_queries
    if num_classes is not None:
        model_kwargs["num_classes"] = num_classes
    if num_select is not None:
        model_kwargs["num_select"] = num_select
    print(f"Creating model {model_cls.__name__} with kwargs: {model_kwargs}")
    if pretrain_weights:
        return model_cls(pretrain_weights=pretrain_weights, **model_kwargs)
    if model_name and os.path.exists(model_name):
        return model_cls(pretrain_weights=model_name, **model_kwargs)
    return model_cls(**model_kwargs)


def _split_name(split, file_name):
    prefix = f"{split}/"
    if file_name.startswith(prefix):
        return file_name[len(prefix):]
    return os.path.basename(file_name)


def _link_or_copy(src, dst):
    if dst.exists():
        return
    try:
        dst.symlink_to(src)
    except OSError:
        shutil.copy2(src, dst)


def prepare_rfdetr_dataset(coco_dir, images_root, work_dir):
    """Create the split layout expected by rfdetr from this repo's COCO files.

    This repository stores annotations as coco_dir/instances_train.json and image
    file names as train/foo.png under images_root. The rfdetr package expects
    train/_annotations.coco.json beside the split images. This function writes a
    lightweight adapter dataset with symlinks to the original images.
    """
    coco_dir = Path(coco_dir)
    images_root = Path(images_root)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    made_any = False
    for split in ("train", "valid", "test"):
        src_ann = coco_dir / f"instances_{split}.json"
        if not src_ann.exists():
            continue
        split_dir = work_dir / split
        split_dir.mkdir(parents=True, exist_ok=True)
        with src_ann.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for image in data.get("images", []):
            original_name = image["file_name"]
            adapted_name = _split_name(split, original_name)
            src_img = images_root / original_name
            if not src_img.exists():
                src_img = images_root / split / adapted_name
            if not src_img.exists():
                raise FileNotFoundError(f"Image referenced by {src_ann} was not found: {original_name}")
            _link_or_copy(src_img.resolve(), split_dir / adapted_name)
            image["file_name"] = adapted_name
        with (split_dir / "_annotations.coco.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        made_any = True

    if not made_any:
        raise FileNotFoundError(f"No instances_*.json files found under {coco_dir}")
    return str(work_dir)


def training_kwargs_from_args(args):
    kwargs = {
        "dataset_dir": args.dataset_dir,
        "output_dir": args.output_dir,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "grad_accum_steps": args.grad_accum_steps,
        "lr": args.lr,
        "lr_encoder": args.lr_encoder,
        "weight_decay": args.weight_decay,
        "use_ema": args.use_ema,
        "gradient_checkpointing": args.gradient_checkpointing,
        "checkpoint_interval": args.checkpoint_interval,
        "resume": args.resume,
        "tensorboard": args.tensorboard,
        "wandb": args.wandb,
        "project": args.wandb_project,
        "run": args.run_name,
        "eval_max_dets": args.max_detections,
        "eval_interval": args.eval_interval,
        "log_per_class_metrics": args.log_per_class_metrics,
        "progress_bar": args.progress_bar,
        "accelerator": args.accelerator,
        "seed": args.seed,
        "lr_scheduler": args.lr_scheduler,
        "lr_min_factor": args.lr_min_factor,
        "warmup_epochs": args.warmup_epochs,
        "drop_path": args.drop_path,
        "compute_val_loss": args.compute_val_loss,
        "compute_test_loss": args.compute_test_loss,
        "fp16_eval": args.fp16_eval,
        "pin_memory": args.pin_memory,
        "persistent_workers": args.persistent_workers,
        "prefetch_factor": args.prefetch_factor,
        "num_workers": args.num_workers,
    }
    if getattr(args, "aug_config", None) is not None:
        kwargs["aug_config"] = args.aug_config
    if args.resolution is not None:
        kwargs["resolution"] = args.resolution
    if getattr(args, "early_stopping", None) is not None:
        kwargs["early_stopping"] = args.early_stopping
        kwargs["early_stopping_patience"] = args.early_stopping_patience
        kwargs["early_stopping_min_delta"] = args.early_stopping_min_delta
        kwargs["early_stopping_use_ema"] = args.early_stopping_use_ema
    return {k: v for k, v in kwargs.items() if v is not None}


def build_label_to_catid(annotation_file):
    from pycocotools.coco import COCO

    coco = COCO(annotation_file)
    cats = sorted(coco.loadCats(coco.getCatIds()), key=lambda x: x["id"])
    return {i: c["id"] for i, c in enumerate(cats)}


def xyxy_to_xywh(box):
    x0, y0, x1, y1 = box
    return [float(x0), float(y0), float(x1 - x0), float(y1 - y0)]


def iou_xywh(box_a, box_b):
    x_a = max(box_a[0], box_b[0])
    y_a = max(box_a[1], box_b[1])
    x_b = min(box_a[0] + box_a[2], box_b[0] + box_b[2])
    y_b = min(box_a[1] + box_a[3], box_b[1] + box_b[3])
    inter_w = max(0.0, x_b - x_a)
    inter_h = max(0.0, y_b - y_a)
    inter_area = inter_w * inter_h
    union = box_a[2] * box_a[3] + box_b[2] * box_b[3] - inter_area
    return inter_area / union if union > 0 else 0.0


def detections_to_arrays(detections):
    import numpy as np

    boxes = np.asarray(getattr(detections, "xyxy", np.empty((0, 4))), dtype=float)
    scores = np.asarray(getattr(detections, "confidence", np.empty((0,))), dtype=float)
    labels = np.asarray(getattr(detections, "class_id", np.empty((0,), dtype=int)), dtype=int)
    return boxes, scores, labels
