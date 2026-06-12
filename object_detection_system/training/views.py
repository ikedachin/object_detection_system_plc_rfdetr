from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from .models import TrainingRun
from annotator.models import Project
from training.applications.rfdetr_train import run_rfdetr_training
import os, json
from django.conf import settings
from pathlib import Path
import torch
from datetime import datetime


RFDETR_DETAIL_PARAM_TYPES = {
    'epochs': int,
    'resolution': int,
    'batch_size': int,
    'grad_accum_steps': int,
    'lr': float,
    'lr_encoder': float,
    'weight_decay': float,
    'accelerator': str,
    'num_workers': int,
    'use_ema': bool,
    'gradient_checkpointing': bool,
    'checkpoint_interval': int,
    'resume': str,
    'pretrain_weights': str,
    'tensorboard': bool,
    'wandb': bool,
    'project': str,
    'run': str,
    'eval_max_dets': int,
    'eval_interval': int,
    'log_per_class_metrics': bool,
    'progress_bar': str,
    'seed': int,
    'lr_scheduler': str,
    'lr_min_factor': float,
    'warmup_epochs': float,
    'drop_path': float,
    'compute_val_loss': bool,
    'compute_test_loss': bool,
    'fp16_eval': bool,
    'pin_memory': bool,
    'persistent_workers': bool,
    'prefetch_factor': int,
    'early_stopping': bool,
    'early_stopping_patience': int,
    'early_stopping_min_delta': float,
    'early_stopping_use_ema': bool,
    'aug_config': object,
    'num_queries': int,
    'num_select': int,
}

RFDETR_DETAIL_PARAM_ALIASES = {
    'workers': 'num_workers',
    'grad_accumulation_steps': 'grad_accum_steps',
    'augmentation': 'aug_config',
    'device': 'accelerator',
    'wandb_project': 'project',
    'run_name': 'run',
    'max_detections': 'eval_max_dets',
}


device = 'cuda:0' if torch.cuda.is_available() else 'cpu'


def resolve_project(value):
    if not value:
        return None
    query = Project.objects.all()
    if str(value).isdigit():
        project = query.filter(id=value).first()
        if project:
            return project
    return query.filter(name=value).first() or query.filter(folder_name=value).first()


def project_dataset_dir(project, data_type):
    return Path(settings.PROJECTS_DIR) / project.folder_name / 'annotated' / data_type


# DBのProjectからプロジェクト名を取得する。YAMLが未生成でもプロジェクトは選択できるようにする。
def get_projects_with_yaml(data_type):
    projects = []
    db_projects = Project.objects.all().order_by('name')
    for project in db_projects:
        if project.name.startswith('.'):
            continue
        annotated_path = project_dataset_dir(project, data_type)
        yamls = list(annotated_path.glob('*.yaml')) + list(annotated_path.glob('*.yml'))
        training_runs = TrainingRun.objects.filter(project=project).order_by('-trained_at')
        projects.append({
            'id': project.id,
            'name': project.name,
            'folder_name': project.folder_name,
            'is_active': getattr(project, 'is_active', False),
            'has_dataset_yaml': bool(yamls),
            'training_runs': list(training_runs.values('id', 'training_name', 'is_active', 'trained_at'))
        })
    return projects


def get_dataset_yamls(project_name, data_type):
    project = resolve_project(project_name)
    if not project:
        return []
    base = project_dataset_dir(project, data_type)
    yamls = list(base.glob('*.yaml')) + list(base.glob('*.yml'))
    return [{'name': y.name, 'fullpath': str(y)} for y in sorted(yamls)]


def parse_bool(value, name):
    if isinstance(value, bool):
        return value
    if value in (None, ''):
        raise ValueError(f'{name}にはtrueまたはfalseを入力してください')
    normalized = str(value).strip().lower()
    if normalized in {'true', '1', 'yes', 'on'}:
        return True
    if normalized in {'false', '0', 'no', 'off'}:
        return False
    raise ValueError(f'{name}にはtrueまたはfalseを入力してください')


def coerce_detail_param(name, value):
    target_type = RFDETR_DETAIL_PARAM_TYPES[name]
    if value in (None, ''):
        return None
    if target_type is bool:
        return parse_bool(value, name)
    if target_type is object:
        return value
    try:
        return target_type(value)
    except (TypeError, ValueError):
        raise ValueError(f'{name}の値が不正です')


def normalize_rfdetr_detail_params(params):
    normalized = {}
    unsupported = []
    for raw_name, value in params.items():
        name = RFDETR_DETAIL_PARAM_ALIASES.get(raw_name, raw_name)
        if name not in RFDETR_DETAIL_PARAM_TYPES:
            unsupported.append(raw_name)
            continue
        normalized_value = coerce_detail_param(name, value)
        if normalized_value is not None:
            normalized[name] = normalized_value
    if unsupported:
        raise ValueError(f'RF-DETRで未対応の詳細パラメータです: {", ".join(sorted(unsupported))}')
    return normalized


def parse_aug_config(value):
    if value in (None, ''):
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        raise ValueError('aug_configはJSONオブジェクト、JSON配列、または空欄で入力してください')
    if not isinstance(parsed, (dict, list)):
        raise ValueError('aug_configはJSONオブジェクト、JSON配列、または空欄で入力してください')
    return parsed


def get_int_param(data, primary, legacy, default):
    raw_value = data.get(primary)
    if raw_value in (None, '') and legacy:
        raw_value = data.get(legacy)
    if raw_value in (None, ''):
        raw_value = default
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f'{primary}には整数を入力してください')


@csrf_exempt
def train_view(request):
    if request.method == 'POST':
        if request.POST.get('yaml_edit_path'):
            # yamlファイル内容書き換えAPI
            yaml_path = request.POST.get('yaml_edit_path')
            yaml_content = request.POST.get('yaml_content')
            if not yaml_path or not os.path.isfile(yaml_path):
                return HttpResponseBadRequest('Invalid yaml path')
            try:
                with open(yaml_path, 'w', encoding='utf-8') as f:
                    f.write(yaml_content)
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})

        # 通常の学習リクエスト
        data = request.POST
        project_id = data.get('project_id')
        training_name = data.get('training_name', '').strip()
        data_type = data.get('data_type')
        dataset_yaml = data.get('dataset_yaml_fullpath') or data.get('dataset_yaml')
        model_name = data.get('model_name') or 'Roboflow/rf-detr-large'
        try:
            epochs = get_int_param(data, 'epochs', None, 100)
            resolution = get_int_param(data, 'resolution', 'imgsz', 640)
            batch_size = get_int_param(data, 'batch_size', 'batch', 16)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})
        other_params = data.get('other_params', '{}')
        
        try:
            project = get_object_or_404(Project, id=project_id)
        except:
            return JsonResponse({'success': False, 'error': 'プロジェクトが見つかりません'})
        
        # 学習名がない場合はデフォルト生成
        if not training_name:
            now = datetime.now()
            training_name = f"{project.name}_{now.strftime('%Y%m%d_%H%M%S')}"
        
        # 同じプロジェクト内で学習名が重複していないかチェック
        if TrainingRun.objects.filter(project=project, training_name=training_name).exists():
            return JsonResponse({'success': False, 'error': '同じ学習名が既に存在します'})
        
        if not dataset_yaml or not os.path.isfile(dataset_yaml):
            return JsonResponse({'success': False, 'error': 'データセットyamlが見つかりません。アノテーション分割を実行してください'})

        try:
            other_params = json.loads(other_params)
            if not isinstance(other_params, dict):
                raise ValueError
        except Exception:
            return JsonResponse({'success': False, 'error': '詳細パラメータはJSONオブジェクト形式で入力してください'})

        try:
            detail_params = normalize_rfdetr_detail_params(other_params)
            aug_config = parse_aug_config(data.get('aug_config'))
            detail_params.pop('epochs', None)
            detail_params.pop('resolution', None)
            detail_params.pop('batch_size', None)
            detail_params['grad_accum_steps'] = get_int_param(data, 'grad_accum_steps', 'grad_accumulation_steps', 4)
            detail_params['num_workers'] = get_int_param(data, 'num_workers', 'workers', 0)
            accelerator = data.get('accelerator')
            if accelerator:
                detail_params['accelerator'] = str(accelerator)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

        if aug_config is not None:
            detail_params['aug_config'] = aug_config
        
        # save_dirを学習名ベースに変更
        save_dir = Path(settings.PROJECTS_DIR) / project.folder_name / 'models' / training_name
        print(f"debug: save_dir={save_dir}")
        save_dir = save_dir.relative_to(Path(settings.PROJECTS_DIR))
        print(f"Training will be saved to: {save_dir}")
        
        try:
            metrics, best_model_path, config_yaml_path, all_params = run_rfdetr_training(
                model_name,
                dataset_yaml,
                epochs=epochs,
                resolution=resolution,
                batch_size=batch_size,
                device=device,
                save_dir=save_dir,
                **detail_params,
            )
        except ImportError as e:
            return JsonResponse({'success': False, 'error': f'RF-DETR学習依存関係が不足しています: {e}'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'RF-DETR学習に失敗しました: {e}'})

        for key, value in all_params.items():
            print(f"{key}: {value}")

        # DB登録
        dataset_yaml_relative = Path(dataset_yaml).relative_to(Path(settings.PROJECT_ROOT)).as_posix()
        saved_model_path = Path(best_model_path).relative_to(Path(settings.PROJECT_ROOT)).as_posix()
        config_yaml_path_relative = Path(config_yaml_path).relative_to(Path(settings.PROJECT_ROOT)).as_posix()

        run = TrainingRun.objects.create(
            project=project,
            training_name=training_name,
            data_type=data_type,
            dataset_yaml=dataset_yaml_relative,
            model_name=model_name,
            epochs=epochs,
            imgsz=str(resolution),
            batch=batch_size,
            other_params=detail_params,
            saved_model_path=saved_model_path,
            config_yaml_path=config_yaml_path_relative,
            metrics=metrics or {},
            is_active=True  # 新しく学習したモデルをアクティブにする
        )
        
        # Projectの情報も更新
        project.active_yaml_path = dataset_yaml_relative
        project.active_weight_path = saved_model_path
        project.save()

        return JsonResponse({
            'success': True, 
            'model_path': best_model_path, 
            'config_yaml_path': config_yaml_path,
            'training_name': training_name,
            'metrics': metrics
        })
    elif request.method == 'GET' and request.GET.get('yaml_path'):
        # yamlファイル内容取得API
        yaml_path = request.GET.get('yaml_path')
        if not yaml_path or not os.path.isfile(yaml_path):
            return HttpResponseBadRequest('Invalid yaml path')
        with open(yaml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/plain; charset=utf-8')
    # プロジェクト名＋data_typeでyamlリストのみ返すAPI
    elif request.method == 'GET' and request.GET.get('project_name') and request.GET.get('data_type'):
        project_name = request.GET.get('project_name')
        data_type = request.GET.get('data_type')
        yamls = get_dataset_yamls(project_name, data_type)
        return JsonResponse({'yamls': yamls})
    else:
        # デフォルトはdata_collectionでプロジェクトリストを取得
        data_type = request.GET.get('data_type', 'data_collection')
        projects = get_projects_with_yaml(data_type)
        # is_active=Trueのプロジェクト名を取得（なければNone）
        selected_project = None
        for p in projects:
            if p.get('is_active'):
                selected_project = p['name']
                break
        # デフォルト選択プロジェクトがなければ最初のもの
        if not selected_project and projects:
            selected_project = projects[0]['name']
        dataset_yamls = get_dataset_yamls(selected_project, data_type) if selected_project else []
        return render(request, 'training/training_index.html', {
            'projects': projects,
            'dataset_yamls': dataset_yamls,
            'selected_data_type': data_type,
            'selected_project': selected_project,
        })


@csrf_exempt
def training_management_view(request):
    """学習管理ビュー"""
    if request.method == 'POST':
        action = request.POST.get('action')
        training_id = request.POST.get('training_id')
        
        if action == 'set_active':
            try:
                training_run = get_object_or_404(TrainingRun, id=training_id)
                training_run.set_active()
                return JsonResponse({'success': True, 'message': f'{training_run.training_name}をアクティブにしました'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        
        elif action == 'delete':
            try:
                training_run = get_object_or_404(TrainingRun, id=training_id)
                training_name = training_run.training_name
                # モデルファイルの削除も考慮（実装は省略）
                training_run.delete()
                return JsonResponse({'success': True, 'message': f'{training_name}を削除しました'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
    
    # プロジェクト一覧と学習履歴を取得
    projects = Project.objects.all().prefetch_related('training_runs')
    return render(request, 'training/management.html', {
        'projects': projects,
    })
