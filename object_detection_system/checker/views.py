from django.shortcuts import render, redirect, get_object_or_404
from annotator.models import Project
from training.models import TrainingRun
from django import forms
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import glob
import json
import threading
import time
from pathlib import Path
from django.conf import settings
from checker.applications.detect import detect_objects
from checker.applications.rfdetr_model import load_model_for_training_run
import yaml


model = None  # グローバル変数としてモデルを定義
model_loading = False  # モデルロード中フラグ
model_loaded_training_id = None  # 現在ロードされているモデルの学習ID

# Create your views here.


def resolve_project_root_path(path_value):
    path = Path(str(path_value).replace('\\', '/'))
    if path.is_absolute():
        return path
    return Path(settings.PROJECT_ROOT) / path

def checker_index(request):
    print("Index view called")
    project_list = Project.objects.all()
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)

    active_project = Project.objects.filter(is_active=True).first()
    active_training = None
    training_runs = []

    active_project_id = None
    active_config_filename = None
    config_files = []
    initial_model_load_training_id = None
    initial_model_load_pending = False

    try:
        if active_project:
            # アクティブプロジェクトの学習一覧を取得
            training_runs = TrainingRun.objects.filter(project=active_project).order_by('-trained_at')
            # アクティブな学習を取得
            active_training = TrainingRun.objects.filter(project=active_project, is_active=True).first()
            
            if not active_training and training_runs.exists():
                # アクティブな学習がない場合は最新の学習をアクティブにする
                active_training = training_runs.first()
                active_training.set_active()
            
            if active_training and active_training.saved_model_path:
                print(f"Active training model path: {active_training.saved_model_path}")
                selected_project = active_project.name
                active_project_id = active_project.id
                # 設定ファイルから設定ファイル名を取得
                active_config_filename = os.path.basename(active_training.config_yaml_path) if active_training.config_yaml_path else ""
                models_path = resolve_project_root_path(active_training.saved_model_path)

                global model, model_loaded_training_id, model_loading

                if models_path.exists():
                    initial_model_load_training_id = active_training.id
                    initial_model_load_pending = model_loading or model is None or model_loaded_training_id != active_training.id
                    if initial_model_load_pending:
                        print(f"Model will be loaded asynchronously: {active_training.training_name}")
                    else:
                        print(f"Model already loaded for training: {active_training.training_name}")
                else:
                    print(f'ウエイトファイルが存在しません: {models_path}')
                    model = None
                    model_loaded_training_id = None
            else:
                print("アクティブな学習または保存されたモデルパスが見つかりません")
                selected_project = active_project.name if active_project else None
                model = None
                model_loaded_training_id = None
        else:
            selected_project = request.session.get('selected_project', None)
            print("アクティブなプロジェクトが見つかりません")
            model = None
            model_loaded_training_id = None
    except Exception as e:
        result_message = f"エラーが発生しました: {str(e)}"
        print(f"Error in checker_index: {e}")

    return render(request, 'checker_index.html', {
        'project_list': project_list,
        'training_runs': training_runs,
        'active_training': active_training,
        'csrf_token': csrf_token,
        'selected_project': selected_project,
        'active_project_id': active_project_id,
        'active_config_filename': active_config_filename,
        'initial_model_load_training_id': initial_model_load_training_id,
        'initial_model_load_pending': initial_model_load_pending,
        'model_loading': model_loading,
        'result_message': None if 'result_message' not in locals() else result_message,
    })


# def get_imgs(request):
#     print("get imgs view called")
#     return render(request, 'get_imgs.html')

class ProjectSelectForm(forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.all(), label='プロジェクト選択')
    config_filename = forms.CharField(label='設定ファイル名', max_length=255)


# def select_project(request):
#     weight_path = None
#     weight_exists = False
#     if request.method == 'POST':
#         form = ProjectSelectForm(request.POST)
#         if form.is_valid():
#             project = form.cleaned_data['project']
#             config_filename = form.cleaned_data['config_filename']
#             weight_path = project.get_weight_path(config_filename)
#             # ファイル存在チェック
#             weight_exists = os.path.exists(weight_path)
#     else:
#         form = ProjectSelectForm()
#     result_message = None
#     if weight_path:
#         if weight_exists:
#             result_message = f"ウエイトファイルが存在します: {weight_path}"
#         else:
#             result_message = f"ウエイトファイルが存在しません: {weight_path}"
#     return render(request, 'select_project.html', {'form': form, 'weight_path': weight_path, 'result_message': result_message})


# def get_config_files(request):
#     """
#     プロジェクトIDを受けて、modelsフォルダ配下の設定ファイル一覧（.yaml）を返すAPI
#     """
#     import glob
#     project_id = request.GET.get('project_id')
#     config_files = []
#     print(f"[DEBUG] project_id: {project_id}")
#     if project_id:
#         try:
#             project = Project.objects.get(id=project_id)
#             # models_dir = os.path.join(project.get_project_path(), 'models')
#             BASE_DIR = settings.BASE_DIR  # object_detection_systemのルートディレクトリを取得
#             models_dir = Path(BASE_DIR).parent / project.get_project_path() / 'models'   # pathlibを使用してパスを扱う
#             print(f"[DEBUG] models_dir: {models_dir}")
#             if os.path.exists(models_dir):
#                 # models配下を再帰的に検索
#                 files_found = glob.glob(os.path.join(models_dir, '**', '*.yaml'), recursive=True)
#                 print(f"[DEBUG] yaml files: {files_found}")
#                 config_files = [os.path.relpath(f, models_dir) for f in files_found]
#             else:
#                 print(f"[DEBUG] models_dir not found: {models_dir}")
#         except Project.DoesNotExist:
#             print(f"[DEBUG] Project not found: {project_id}")
#     return JsonResponse({'config_files': config_files})


def get_weight_path(request):
    """
    プロジェクトIDと設定ファイル名からウエイトパスと存在判定を返すAPI
    """
    project_id = request.GET.get('project_id')
    config_filename = request.GET.get('config_filename')
    weight_path = None
    weight_exists = False
    result_message = ""
    BASE_DIR = settings.BASE_DIR  # object_detection_systemのルートディレクトリを取得
    if project_id and config_filename:
        try:
            project = Project.objects.get(id=project_id)
            weight_path = project.get_weight_path(config_filename)
            weight_exists = os.path.exists(weight_path)
            if weight_exists:
                result_message = f"ウエイトファイルが存在します: {weight_path}"
                global model
                training_run = TrainingRun.objects.filter(project=project, saved_model_path__endswith=Path(weight_path).name).first()
                if training_run:
                    model = load_model_for_training_run(training_run)
            else:
                result_message = f"ウエイトファイルが存在しません: {weight_path}"
        except Project.DoesNotExist:
            result_message = "プロジェクトが見つかりません"
    else:
        result_message = "パラメータが不足しています"
    return JsonResponse({
        'weight_path': weight_path,
        'weight_exists': weight_exists,
        'result_message': result_message
    })


@csrf_exempt
def set_active_project(request):
    """プロジェクトをアクティブにするAPI"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')
            
            if not project_id:
                return JsonResponse({'success': False, 'error': 'プロジェクトIDが必要です'})
            
            # 既存のアクティブプロジェクトを無効化
            Project.objects.filter(is_active=True).update(is_active=False)
            
            # 指定されたプロジェクトをアクティブ化
            project = get_object_or_404(Project, id=project_id)
            project.is_active = True
            project.save()
            
            return JsonResponse({
                'success': True,
                'message': f'プロジェクト "{project.name}" をアクティブにしました'
            })
        except Project.DoesNotExist:
            return JsonResponse({'success': False, 'error': '指定されたプロジェクトが見つかりません'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})


@csrf_exempt
def set_active_training(request):
    """学習モデルをアクティブにするAPI"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            training_id = data.get('training_id')
            
            if not training_id:
                return JsonResponse({'success': False, 'error': '学習IDが必要です'})
            
            # 指定された学習をアクティブ化
            training_run = get_object_or_404(TrainingRun, id=training_id)
            training_run.set_active()
            
            # プロジェクトもアクティブにする
            if not training_run.project.is_active:
                Project.objects.filter(is_active=True).update(is_active=False)
                training_run.project.is_active = True
                training_run.project.save()
            
            return JsonResponse({
                'success': True,
                'message': f'学習モデル "{training_run.training_name}" をアクティブにしました'
            })
        except TrainingRun.DoesNotExist:
            return JsonResponse({'success': False, 'error': '指定された学習が見つかりません'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})


def load_model_async(training_run):
    """
    非同期でモデルをロードする関数
    """
    global model, model_loading, model_loaded_training_id
    
    try:
        model_loading = True
        print(f"モデルロード開始: {training_run.training_name}")
        
        # モデルパスの確認
        if not training_run.saved_model_path:
            raise Exception("モデルパスが設定されていません")
        
        models_path = resolve_project_root_path(training_run.saved_model_path)
        if not models_path.exists():
            raise Exception(f"モデルファイルが存在しません: {models_path}")
        
        print(f"RF-DETRモデルロード中: {models_path}")
        model = load_model_for_training_run(training_run)
        model_loaded_training_id = training_run.id
        
        print(f"モデルロード完了: {training_run.training_name}")
        
    except Exception as e:
        print(f"モデルロードエラー: {e}")
        model = None
        model_loaded_training_id = None
    finally:
        model_loading = False


@csrf_exempt
def load_model_for_training(request):
    """
    指定された学習モデルをロードするAPI
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            training_id = data.get('training_id')
            
            if not training_id:
                return JsonResponse({'success': False, 'error': '学習IDが必要です'})
            
            training_run = get_object_or_404(TrainingRun, id=training_id)
            
            # 既に同じモデルがロードされている場合はスキップ
            global model_loaded_training_id, model_loading
            if model_loaded_training_id == training_id and model is not None:
                return JsonResponse({
                    'success': True,
                    'message': 'モデルは既にロードされています',
                    'status': 'loaded'
                })
            
            # 現在ロード中の場合
            if model_loading:
                return JsonResponse({
                    'success': True,
                    'message': 'モデルロード中です...',
                    'status': 'loading'
                })
            
            # 非同期でモデルをロード
            thread = threading.Thread(target=load_model_async, args=(training_run,))
            thread.daemon = True
            thread.start()
            
            return JsonResponse({
                'success': True,
                'message': f'モデル "{training_run.training_name}" のロードを開始しました',
                'status': 'loading'
            })
            
        except TrainingRun.DoesNotExist:
            return JsonResponse({'success': False, 'error': '指定された学習が見つかりません'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})


@csrf_exempt
def check_model_status(request):
    """
    モデルのロード状況を確認するAPI
    """
    global model, model_loading, model_loaded_training_id
    
    if model_loading:
        status = 'loading'
        message = 'モデルロード中...'
    elif model is not None and model_loaded_training_id is not None:
        try:
            training_run = TrainingRun.objects.get(id=model_loaded_training_id)
            status = 'loaded'
            message = f'モデル "{training_run.training_name}" がロードされています'
        except TrainingRun.DoesNotExist:
            status = 'error'
            message = 'ロードされたモデルの情報が見つかりません'
    else:
        status = 'not_loaded'
        message = 'モデルがロードされていません'
    
    return JsonResponse({
        'success': True,
        'status': status,
        'message': message,
        'model_loaded_training_id': model_loaded_training_id
    })


@csrf_exempt
def reset_plc_result_signals(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})

    try:
        from checker.applications.plc_monitor import reset_result_signals

        reset_targets = reset_result_signals()
        return JsonResponse({
            'success': True,
            'message': 'PLC結果ビットをリセットしました',
            'reset_targets': reset_targets,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def latest_plc_result(request):
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'GETリクエストが必要です'})

    from checker.applications.plc_monitor import get_latest_plc_result

    return JsonResponse({
        'success': True,
        'result': get_latest_plc_result(),
    })

