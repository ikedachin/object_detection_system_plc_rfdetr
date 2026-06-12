import argparse
import math
import os
import random
from contextlib import contextmanager

import numpy as np
import torch
import yaml


TRAIN_CONFIG_SECTIONS = {
    "dataset",
    "model",
    "training",
    "optimizer",
    "scheduler",
    "hardware",
    "checkpoint",
    "early_stopping",
    "logging",
    "evaluation",
    "dataloader",
    "augmentation",
}

ALIASES = {
    "dataset_dir": "coco_dir",
    "output_dir": "output_dir",
    "project": "wandb_project",
    "run": "run_name",
    "eval_max_dets": "max_detections",
    "grad_accumulation_steps": "grad_accum_steps",
    "workers": "num_workers",
}

OPTIONAL_SCRIPT_KEYS = {
    "early_stopping",
    "early_stopping_patience",
    "early_stopping_min_delta",
    "early_stopping_use_ema",
    "early_stopping_metric",
}


def _flatten_config(data, section=None):
    if not data:
        return {}
    flat = {}
    for key, value in data.items():
        if key in TRAIN_CONFIG_SECTIONS and isinstance(value, dict):
            flat.update(_flatten_config(value, section=key))
        else:
            target = ALIASES.get(key, key)
            if section == "early_stopping" and key == "enabled":
                target = "early_stopping"
            elif section == "logging" and key == "project":
                target = "wandb_project"
            elif section == "logging" and key == "run":
                target = "run_name"
            elif section == "augmentation" and key == "config":
                target = "aug_config"
            flat[target] = value
    return flat


def _cli_option_names(parser):
    names = set()
    for action in parser._actions:
        for option in action.option_strings:
            if option.startswith("--"):
                names.add(option[2:])
    return names


def parse_args_with_config(parser):
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument("-c", "--config", help="YAML training config file")
    config_args, remaining = config_parser.parse_known_args()
    config_values = {}
    if config_args.config:
        with open(config_args.config, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        config_values = _flatten_config(loaded)

    valid_names = {name.replace("-", "_") for name in _cli_option_names(parser)}
    defaults = {k: v for k, v in config_values.items() if k in valid_names}
    if defaults:
        parser.set_defaults(**defaults)
    args = parser.parse_args(remaining)
    args.config = config_args.config
    unknown = sorted(k for k in config_values if k not in valid_names and k not in OPTIONAL_SCRIPT_KEYS)
    if unknown:
        print(f"Warning: YAML config has unsupported keys and they were ignored: {', '.join(unknown)}")
    return args


def add_training_arguments(parser, include_early_stopping=False):
    parser.add_argument("-c", "--config", help="YAML training config file")
    parser.add_argument("-d", "--coco-dir", default="coco_dataset", help="COCO dataset dir containing instances_train.json / instances_valid.json")
    parser.add_argument("-i", "--images-root", default=None, help="images root directory (file_name in JSON is relative to this root)")
    parser.add_argument("-m", "--model-name", default="Roboflow/rf-detr-large", help="pretrained model name / path")
    parser.add_argument("-o", "--output-dir", default="./rf_detr_finetuned", help="where to save checkpoints")
    parser.add_argument("--pretrain-weights", default=None, help="model directory/name used to initialize weights before fresh training")
    parser.add_argument("--resume", default=None, help="resume from a training_state.pt/checkpoint.pth file or a checkpoint directory")
    parser.add_argument("-b", "--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum-steps", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--lr-encoder", type=float, default=1.5e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--clip-grad-norm", type=float, default=0.1)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--resolution", type=int, default=None)
    parser.add_argument("--accelerator", default="auto", help="auto, cuda/gpu, cpu, or mps")
    parser.add_argument("--devices", default=1, help='number of CUDA devices or "auto"')
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--gradient-checkpointing", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--use-ema", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ema-decay", type=float, default=0.9999)
    parser.add_argument("--drop-path", type=float, default=0.0)
    parser.add_argument("--checkpoint-interval", type=int, default=10)
    parser.add_argument("--skip-best-epochs", type=int, default=0)
    parser.add_argument("--lr-scheduler", choices=["step", "cosine", "linear"], default="step")
    parser.add_argument("--lr-drop", type=int, default=100)
    parser.add_argument("--lr-min-factor", type=float, default=0.0)
    parser.add_argument("--warmup-epochs", type=float, default=0.0)
    parser.add_argument("--log-interval", type=int, default=10)
    parser.add_argument("--progress-bar", default=None, help='None, "tqdm", "rich", true, or false')
    parser.add_argument("--tensorboard", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--wandb", action=argparse.BooleanOptionalAction, default=False, help="Enable wandb logging")
    parser.add_argument("--wandb-project", help="wandb project name")
    parser.add_argument("--wandb-entity", help="wandb entity (username or team name)")
    parser.add_argument("--run-name", help="wandb run name")
    parser.add_argument("--num-workers", type=int, default=0, help="number of DataLoader workers")
    parser.add_argument("--pin-memory", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--persistent-workers", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--prefetch-factor", type=int, default=None)
    parser.add_argument("--aug-config", default=None, help="YAML dict, inline JSON/YAML dict, or preset name for Albumentations")
    parser.add_argument("--eval-metrics", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--eval-score-thresh", type=float, default=0.05)
    parser.add_argument("--eval-iou-thresh", type=float, default=0.5)
    parser.add_argument("--max-detections", type=int, default=500)
    parser.add_argument("--eval-interval", type=int, default=1)
    parser.add_argument("--log-per-class-metrics", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--compute-val-loss", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--compute-test-loss", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--fp16-eval", action=argparse.BooleanOptionalAction, default=False)
    if include_early_stopping:
        parser.add_argument("--early-stopping", action=argparse.BooleanOptionalAction, default=False)
        parser.add_argument("--early-stopping-patience", type=int, default=10)
        parser.add_argument("--early-stopping-min-delta", type=float, default=0.001)
        parser.add_argument("--early-stopping-use-ema", action=argparse.BooleanOptionalAction, default=False)
        parser.add_argument("--early-stopping-metric", choices=["map50", "map50_95", "val_loss"], default="map50_95")
    return parser


def finalize_args(args):
    if not args.images_root:
        raise ValueError("--images-root is required unless images_root is set in YAML")
    args.grad_accum_steps = max(1, int(args.grad_accum_steps))
    args.checkpoint_interval = max(1, int(args.checkpoint_interval))
    args.eval_interval = max(1, int(args.eval_interval))
    args.skip_best_epochs = max(0, int(args.skip_best_epochs))
    args.pin_memory = bool(args.pin_memory) if args.pin_memory is not None else None
    args.persistent_workers = bool(args.persistent_workers) if args.persistent_workers is not None else None
    if args.prefetch_factor is not None and args.num_workers <= 0:
        print("Warning: prefetch_factor requires num_workers > 0; ignoring prefetch_factor.")
        args.prefetch_factor = None
    return args


def set_random_seed(seed):
    if seed is None:
        return
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _mps_available():
    return getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()


def _enable_mps_fallback():
    """PYTORCH_ENABLE_MPS_FALLBACK=1 を自動設定し、未実装演算子をCPUにフォールバックさせる。"""
    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") != "1":
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        print("Info: PYTORCH_ENABLE_MPS_FALLBACK=1 を自動設定しました（MPS未実装演算子はCPUで処理されます）。")


def select_device(args):
    accelerator = (args.accelerator or "auto").lower()

    # accelerator が明示指定されている場合（auto 以外）
    if accelerator != "auto":
        # "gpu" は "cuda" の別名
        target = "cuda" if accelerator == "gpu" else accelerator
        if target == "cuda":
            if torch.cuda.is_available():
                print(f"Info: CUDA デバイスを使用します ({torch.cuda.get_device_name(0)})。")
                return torch.device("cuda")
            print("Warning: CUDA が要求されましたが利用できません。CPUにフォールバックします。")
            return torch.device("cpu")
        if target == "mps":
            if _mps_available():
                _enable_mps_fallback()
                print("Info: Apple Silicon MPS デバイスを使用します。")
                return torch.device("mps")
            print("Warning: MPS が要求されましたが利用できません。CPUにフォールバックします。")
            return torch.device("cpu")
        # cpu など
        return torch.device(target)

    # accelerator == "auto": CUDA → MPS → CPU の優先順位で自動選択
    if torch.cuda.is_available():
        print(f"Info: [auto] CUDA デバイスを使用します ({torch.cuda.get_device_name(0)})。")
        return torch.device("cuda")
    if _mps_available():
        _enable_mps_fallback()
        print("Info: [auto] Apple Silicon MPS デバイスを使用します。")
        return torch.device("mps")
    print("Info: [auto] GPU が見つからないため CPU を使用します。")
    return torch.device("cpu")


def dataloader_kwargs(args):
    kwargs = {"num_workers": args.num_workers}
    if args.pin_memory is not None:
        kwargs["pin_memory"] = args.pin_memory
    if args.persistent_workers is not None and args.num_workers > 0:
        kwargs["persistent_workers"] = args.persistent_workers
    if args.prefetch_factor is not None and args.num_workers > 0:
        kwargs["prefetch_factor"] = args.prefetch_factor
    return kwargs


def configure_processor(processor, resolution):
    if resolution is None:
        return
    processor.size = {"height": resolution, "width": resolution}
    if hasattr(processor, "crop_size"):
        processor.crop_size = {"height": resolution, "width": resolution}


def build_optimizer(model, args):
    encoder_params = []
    other_params = []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if "encoder" in name or "backbone" in name:
            encoder_params.append(param)
        else:
            other_params.append(param)
    groups = []
    if other_params:
        groups.append({"params": other_params, "lr": args.lr})
    if encoder_params:
        groups.append({"params": encoder_params, "lr": args.lr_encoder})
    return torch.optim.AdamW(groups, lr=args.lr, weight_decay=args.weight_decay)


def build_scheduler(optimizer, args, steps_per_epoch):
    total_steps = max(1, math.ceil(steps_per_epoch / args.grad_accum_steps) * args.epochs)
    warmup_steps = int(max(0.0, args.warmup_epochs) * math.ceil(steps_per_epoch / args.grad_accum_steps))
    if args.lr_scheduler == "cosine":
        def cosine_lambda(current_step):
            if warmup_steps > 0 and current_step < warmup_steps:
                return float(current_step) / float(max(1, warmup_steps))
            progress = float(current_step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            cosine = 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))
            return args.lr_min_factor + (1.0 - args.lr_min_factor) * cosine

        return torch.optim.lr_scheduler.LambdaLR(optimizer, cosine_lambda), total_steps
    if args.lr_scheduler == "linear":
        def linear_lambda(current_step):
            if warmup_steps > 0 and current_step < warmup_steps:
                return float(current_step) / float(max(1, warmup_steps))
            progress = float(current_step - warmup_steps) / float(max(1, total_steps - warmup_steps))
            return max(0.0, 1.0 - progress)

        return torch.optim.lr_scheduler.LambdaLR(optimizer, linear_lambda), total_steps

    def lr_lambda(current_step):
        if warmup_steps > 0 and current_step < warmup_steps:
            return float(current_step) / float(max(1, warmup_steps))
        epoch = current_step / max(1, math.ceil(steps_per_epoch / args.grad_accum_steps))
        drops = int(epoch // max(1, args.lr_drop))
        return max(args.lr_min_factor, 0.1 ** drops)

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda), total_steps


class ModelEma:
    def __init__(self, model, decay):
        self.decay = decay
        self.shadow = {k: v.detach().clone() for k, v in unwrap_model(model).state_dict().items() if torch.is_floating_point(v)}
        self.backup = None

    def update(self, model):
        state = unwrap_model(model).state_dict()
        for key, value in state.items():
            if key in self.shadow:
                self.shadow[key].mul_(self.decay).add_(value.detach(), alpha=1.0 - self.decay)

    @contextmanager
    def apply_to(self, model):
        if not self.shadow:
            yield
            return
        target = unwrap_model(model)
        self.backup = {k: v.detach().clone() for k, v in target.state_dict().items() if k in self.shadow}
        target.load_state_dict(self.shadow, strict=False)
        try:
            yield
        finally:
            target.load_state_dict(self.backup, strict=False)
            self.backup = None


def unwrap_model(model):
    return model.module if hasattr(model, "module") else model


def maybe_data_parallel(model, args, device):
    if device.type != "cuda":
        return model
    devices = args.devices
    if isinstance(devices, str) and devices.lower() == "auto":
        count = torch.cuda.device_count()
    else:
        try:
            count = int(devices)
        except (TypeError, ValueError):
            count = 1
    if count > 1 and torch.cuda.device_count() > 1:
        return torch.nn.DataParallel(model, device_ids=list(range(min(count, torch.cuda.device_count()))))
    return model


def save_checkpoint(model, processor, output_dir, optimizer=None, scheduler=None, epoch=None, global_step=None, ema=None, name=None):
    save_dir = os.path.join(output_dir, name) if name else output_dir
    os.makedirs(save_dir, exist_ok=True)
    unwrapped = unwrap_model(model)
    unwrapped.save_pretrained(save_dir)
    processor.save_pretrained(save_dir)
    state = {
        "epoch": epoch,
        "global_step": global_step,
        "model_state_dict": unwrapped.state_dict(),
        "optimizer_state_dict": optimizer.state_dict() if optimizer is not None else None,
        "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
        "ema_state_dict": ema.shadow if ema is not None else None,
    }
    torch.save(state, os.path.join(save_dir, "training_state.pt"))
    torch.save(state, os.path.join(output_dir, "checkpoint.pth"))
    return save_dir


def load_training_state(path, model, optimizer=None, scheduler=None, ema=None, map_location="cpu"):
    state_path = path
    if os.path.isdir(path):
        candidate = os.path.join(path, "training_state.pt")
        state_path = candidate if os.path.exists(candidate) else None
    if not state_path or not os.path.exists(state_path):
        return 0, 0
    state = torch.load(state_path, map_location=map_location)
    unwrap_model(model).load_state_dict(state.get("model_state_dict", state), strict=False)
    if optimizer is not None and state.get("optimizer_state_dict"):
        optimizer.load_state_dict(state["optimizer_state_dict"])
    if scheduler is not None and state.get("scheduler_state_dict"):
        scheduler.load_state_dict(state["scheduler_state_dict"])
    if ema is not None and state.get("ema_state_dict"):
        ema.shadow = state["ema_state_dict"]
    return int(state.get("epoch") or 0), int(state.get("global_step") or 0)


def get_progress_iter(iterable, args, desc=None):
    style = args.progress_bar
    if style in (None, "None", "none", False):
        return iterable
    if style is True or str(style).lower() in {"true", "tqdm", "rich"}:
        try:
            from tqdm.auto import tqdm
            return tqdm(iterable, desc=desc)
        except Exception as exc:
            print(f"Warning: progress_bar requested but tqdm is unavailable: {exc}")
    return iterable


def eval_autocast(device, enabled):
    if not enabled or device.type not in {"cuda", "mps"}:
        return torch.autocast(device_type="cpu", enabled=False)
    return torch.autocast(device_type=device.type, dtype=torch.float16)


def load_aug_config(value):
    if value in (None, "", False):
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and os.path.exists(value):
        with open(value, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("aug_config", data)
    if isinstance(value, str):
        if value.startswith("AUG_"):
            try:
                from rfdetr.datasets import aug_config as presets
                return getattr(presets, value)
            except Exception as exc:
                raise RuntimeError(f"Unable to load RF-DETR augmentation preset {value}") from exc
        try:
            return yaml.safe_load(value)
        except Exception:
            return value
    return value
