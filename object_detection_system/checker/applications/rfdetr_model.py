from pathlib import Path

import yaml
from django.conf import settings

from training.applications.rfdetr_native import create_model


def resolve_project_root_path(path_value):
    path = Path(str(path_value).replace("\\", "/"))
    if path.is_absolute():
        return path
    return Path(settings.PROJECT_ROOT) / path


def load_rfdetr_config(config_path):
    if not config_path:
        return {}
    path = resolve_project_root_path(config_path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("RF_DETR") or {}


def load_model_for_training_run(training_run):
    config = load_rfdetr_config(training_run.config_yaml_path)
    model_path = config.get("model_path") or training_run.saved_model_path
    model_path = resolve_project_root_path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"モデルファイルが見つかりません: {model_path}")
    model_name = config.get("model_name") or training_run.model_name or "Roboflow/rf-detr-large"
    return create_model(
        model_name=model_name,
        pretrain_weights=str(model_path),
        num_queries=config.get("num_queries"),
        num_classes=config.get("num_classes"),
        num_select=config.get("num_select"),
    )
