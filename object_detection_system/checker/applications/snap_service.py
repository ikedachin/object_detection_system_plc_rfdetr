import datetime
import json
import os
import threading
from pathlib import Path
from dataclasses import dataclass

import cv2
import yaml
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from django.conf import settings

from annotator.models import Project
from checker.applications import detect, quality_verify
from checker.applications.get_img import StillCamera
from checker.applications.rfdetr_model import load_model_for_training_run
from get_imgs.applications import camera_get_data
from training.models import TrainingRun


image_size_dict = {
    'HD1080p': {'width': 1920, 'height': 1080},
    'HD720p': {'width': 1280, 'height': 720},
    'SD480p': {'width': 640, 'height': 480},
    'SD360p': {'width': 480, 'height': 360},
}

pixes = image_size_dict['SD480p']
camera = None
snap_lock = threading.Lock()


def resolve_project_root_path(path_value):
    path = Path(str(path_value).replace('\\', '/'))
    if path.is_absolute():
        return path
    return Path(settings.PROJECT_ROOT) / path


def is_snap_running():
    return snap_lock.locked()


@dataclass
class SnapResult:
    message: str
    timestamp: str
    result_dict: dict
    result: bool
    image_bytes: bytes


@database_sync_to_async
def get_active_project():
    return Project.objects.filter(is_active=True).first()


@database_sync_to_async
def get_active_training(project):
    if project:
        return TrainingRun.objects.filter(project=project, is_active=True).first()
    return None


@database_sync_to_async
def get_latest_training(project):
    if project:
        return TrainingRun.objects.filter(project=project).order_by('-trained_at').first()
    return None


def ensure_camera_initialized():
    global camera
    if camera is not None:
        try:
            if getattr(camera, 'cap', None) is not None and camera.cap.isOpened():
                return
        except Exception:
            pass

    try:
        cams = camera_get_data.find_available_cameras()
        src = cams[-1] if cams else 0
    except Exception:
        src = 0
    camera = StillCamera(src, **pixes)


def stop_camera_if_running():
    global camera
    if camera is None:
        return
    try:
        if hasattr(camera, 'stop'):
            camera.stop()
        elif getattr(camera, 'cap', None) is not None:
            camera.cap.release()
    except Exception:
        pass
    finally:
        camera = None


def _capture_frame():
    ensure_camera_initialized()
    frame = camera.get_jpg()
    if frame is None:
        raise RuntimeError('カメラフレームを取得できません')
    print(f'Camera frame shape: {frame.shape if frame is not None else "None"}')
    return frame


async def _ensure_model_loaded():
    from checker import views

    if views.model_loading:
        raise RuntimeError('モデルをロード中です。しばらくお待ちください。')

    if views.model is not None:
        return views.model, views.model_loaded_training_id

    print("モデルがロードされていません。自動ロードを試みます...")
    active_project = await get_active_project()
    if not active_project:
        raise RuntimeError('アクティブなプロジェクトが見つかりません。プロジェクトを選択してください。')

    active_training = await get_active_training(active_project)
    if not active_training or not active_training.saved_model_path:
        raise RuntimeError('アクティブな学習モデルが見つかりません。プロジェクトと学習モデルを選択してください。')

    model_path = active_training.saved_model_path
    model_path = resolve_project_root_path(model_path)

    if not model_path.exists():
        raise RuntimeError(f'モデルファイルが見つかりません: {model_path}')

    try:
        views.model = load_model_for_training_run(active_training)
        views.model_loaded_training_id = active_training.id
        print(f"モデルを自動ロードしました: {active_training.training_name}")
    except Exception as exc:
        print(f"モデルの自動ロードに失敗: {exc}")
        raise RuntimeError('モデルの自動ロードに失敗しました。ページを再読み込みしてください。') from exc

    return views.model, views.model_loaded_training_id


async def _resolve_active_training(model_loaded_training_id):
    active_project = await get_active_project()
    print(f'Active project: {active_project.name if active_project else "None"}')

    if not active_project:
        print('No active project found')
        raise RuntimeError('アクティブなプロジェクトまたは学習モデル、設定ファイルが見つかりません')

    active_training = await get_active_training(active_project)
    print(f'Active training: {active_training.training_name if active_training else "None"}')

    if active_training:
        detect_config_path = active_training.config_yaml_path
        print(f'Config path from active training: {detect_config_path}')

        if model_loaded_training_id != active_training.id:
            raise RuntimeError('ロードされているモデルとアクティブな学習モデルが一致しません。モデルを再ロードしてください。')
    else:
        active_training = await get_latest_training(active_project)
        detect_config_path = active_training.config_yaml_path if active_training else None
        print(f'Using latest training: {active_training.training_name if active_training else "None"}')
        print(f'Config path from latest training: {detect_config_path}')

    return active_project, active_training, detect_config_path


def _load_detect_config(detect_config_path):
    print(f'Final config path: {detect_config_path}')

    if detect_config_path and not os.path.isabs(detect_config_path):
        detect_config_path = resolve_project_root_path(detect_config_path)
        print(f'Converted to absolute path: {detect_config_path}')

    print(f'Config file exists: {Path(detect_config_path).exists() if detect_config_path else "N/A"}')

    if not detect_config_path or not Path(detect_config_path).exists():
        raise RuntimeError('アクティブなプロジェクトまたは学習モデル、設定ファイルが見つかりません')

    try:
        with open(detect_config_path, 'r') as f:
            detect_config = yaml.safe_load(f)
    except Exception as exc:
        raise RuntimeError(f'設定ファイルの読み込みに失敗しました: {str(exc)}') from exc

    if 'RF_DETR' in detect_config:
        rf_detr_config = detect_config['RF_DETR']
        infer_config = dict(rf_detr_config.get('detect_config') or {})
        infer_config['class_names'] = rf_detr_config.get('class_names') or []
        print(f'RF-DETR detect config: {infer_config}')
        return infer_config

    print('Using default RF-DETR config')
    return {
        'conf': 0.45,
        'verbose': False,
    }


def encode_png_from_rgb_array(image_array):
    if image_array.ndim == 3 and image_array.shape[2] == 3:
        image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
    ret, buf = cv2.imencode('.png', image_array)
    if not ret:
        raise RuntimeError("画像のエンコードに失敗しました")
    return buf.tobytes()


async def run_snap_backend() -> SnapResult:
    if not snap_lock.acquire(blocking=False):
        raise RuntimeError('判定中です。現在の処理が完了してから再実行してください。')
    try:
        timestamp = datetime.datetime.now().isoformat()
        frame = _capture_frame()
        model, model_loaded_training_id = await _ensure_model_loaded()

        print(f'Model loaded: {model is not None}, Training ID: {model_loaded_training_id}')
        active_project, active_training, detect_config_path = await _resolve_active_training(model_loaded_training_id)
        rf_detr_detect_config = _load_detect_config(detect_config_path)

        try:
            print(f'Starting inference with model: {type(model)}')
            result_dict, img_array = await detect.detect_objects(
                frame,
                model,
                project=active_project,
                training_run=active_training,
                **rf_detr_detect_config,
            )
            for key, value in result_dict.items():
                print(f'Detect result: key={key}, value={value}')

            predicted_img = img_array[:pixes['height'], :, :]
            image_bytes = encode_png_from_rgb_array(predicted_img)

            result = quality_verify.quality_verify_thr17(result_dict)
            print(f'Approval status: {result}')

            return SnapResult(
                message='Snapshot taken and processed',
                timestamp=timestamp,
                result_dict=result_dict if isinstance(result_dict, dict) else {},
                result=result,
                image_bytes=image_bytes,
            )
        except Exception as exc:
            print(f'推論処理エラー: {exc}')
            raise RuntimeError(f'推論処理中にエラーが発生しました: {str(exc)}') from exc
    finally:
        snap_lock.release()


def run_snap_backend_sync() -> SnapResult:
    return async_to_sync(run_snap_backend)()


def snap_result_to_json(result: SnapResult) -> str:
    return json.dumps({
        'message': result.message,
        'timestamp': result.timestamp,
        'result_dict': result.result_dict,
        'result': result.result,
    })
