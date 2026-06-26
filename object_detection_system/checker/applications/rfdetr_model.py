from pathlib import Path, PureWindowsPath

import yaml
from django.conf import settings

from training.applications.rfdetr_native import create_model


def _rebase_foreign_project_path(path_value, project_root):
    path_text = str(path_value).strip().replace("\\", "/")
    parts = [part for part in path_text.split("/") if part and not part.endswith(":")]

    for marker in (project_root.name, "projects", "settings"):
        if marker in parts:
            marker_index = parts.index(marker)
            relative_parts = parts[marker_index + 1:] if marker == project_root.name else parts[marker_index:]
            return project_root.joinpath(*relative_parts)

    return None


def resolve_project_root_path(path_value):
    project_root = Path(settings.PROJECT_ROOT)
    if path_value is None:
        return project_root

    path_text = str(path_value).strip()
    if not path_text:
        return project_root

    normalized_text = path_text.replace("\\", "/")
    path = Path(normalized_text).expanduser()

    if path.is_absolute():
        return path

    windows_path = PureWindowsPath(path_text)
    if windows_path.is_absolute():
        rebased_path = _rebase_foreign_project_path(path_text, project_root)
        return rebased_path or Path(normalized_text)

    return project_root / normalized_text


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
