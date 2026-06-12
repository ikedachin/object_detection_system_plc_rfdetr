from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import os
import json
from pathlib import Path
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import DataCollectionProject, DataCollectionSession
from annotator.models import Project, ImageFile
from .applications.camera_get_data import available_cameras

# Create your views here.

def index(request):
    # アクティブなプロジェクトと全プロジェクトを取得
    active_project = DataCollectionProject.get_active_project()
    all_projects = DataCollectionProject.objects.all()
    
    context = {
        'active_project': active_project,
        'all_projects': all_projects,
    }
    return render(request, 'index.html', context)


def get_imgs(request):
    print("get imgs view called")
    active_project = DataCollectionProject.get_active_project()
    context = {
        'active_project': active_project,
    }
    return render(request, 'get_imgs.html', context)


@csrf_exempt
def create_project_folders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_name = data.get('project_name')
            description = data.get('description', '')
            
            if not project_name:
                return JsonResponse({'success': False, 'error': 'プロジェクト名がありません'}, status=400)
            
            # フォルダ名を作成（日本語文字を含む場合の対策）
            folder_name = project_name.replace(' ', '_').replace('　', '_')
            
            # データベースにプロジェクトを作成
            project = DataCollectionProject.objects.create(
                name=project_name,
                folder_name=folder_name,
                description=description
            )
            
            # フォルダ構造を作成
            folders = project.create_folder_structure()
            
            # annotatorアプリのProjectモデルとも連携
            try:
                annotator_project = Project.objects.create(
                    name=project_name,
                    folder_name=folder_name
                )
            except Exception as e:
                print(f"Annotator project creation error: {e}")
            
            return JsonResponse({
                'success': True,
                'project_id': project.id,
                'project_name': project_name,
                'folder_name': folder_name,
                'imgs_dir': folders['imgs_dir']
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'}, status=405)


@csrf_exempt
def set_active_project(request):
    """アクティブなプロジェクトを設定"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')
            
            if not project_id:
                return JsonResponse({'success': False, 'error': 'プロジェクトIDがありません'}, status=400)
            
            project = get_object_or_404(DataCollectionProject, id=project_id)
            project.set_active()
            
            # annotatorアプリのProjectモデルとも連携
            try:
                annotator_project = Project.objects.get(folder_name=project.folder_name)
                annotator_project.set_active()
            except Project.DoesNotExist:
                print(f"Annotator project not found for {project.folder_name}")
            
            return JsonResponse({
                'success': True,
                'active_project': {
                    'id': project.id,
                    'name': project.name,
                    'folder_name': project.folder_name
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'}, status=405)


@csrf_exempt
def get_project_stats(request):
    """プロジェクトの統計情報を取得"""
    if request.method == 'GET':
        try:
            project_id = request.GET.get('project_id')
            if project_id:
                project = get_object_or_404(DataCollectionProject, id=project_id)
                project.update_image_counts()
                projects = [project]
            else:
                projects = DataCollectionProject.objects.all()
                for p in projects:
                    p.update_image_counts()
            
            stats = []
            for project in projects:
                stats.append({
                    'id': project.id,
                    'name': project.name,
                    'folder_name': project.folder_name,
                    'auto_image_count': project.auto_image_count,
                    'manual_image_count': project.manual_image_count,
                    'total_image_count': project.total_image_count,
                    'is_active': project.is_active,
                    'created_at': project.created_at.isoformat()
                })
            
            return JsonResponse({'success': True, 'projects': stats})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'GETメソッドのみ対応'}, status=405)


@csrf_exempt
def create_collection_session(request):
    """データ収集セッションを作成"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')
            session_name = data.get('session_name')
            collection_type = data.get('collection_type', 'auto')
            notes = data.get('notes', '')
            
            if not project_id or not session_name:
                return JsonResponse({'success': False, 'error': 'プロジェクトIDとセッション名が必要です'}, status=400)
            
            project = get_object_or_404(DataCollectionProject, id=project_id)
            
            session = DataCollectionSession.objects.create(
                project=project,
                session_name=session_name,
                collection_type=collection_type,
                notes=notes
            )
            
            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'session_name': session.session_name,
                'collection_type': session.collection_type,
                'start_time': session.start_time.isoformat()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'}, status=405)


@csrf_exempt
def get_camera_availability(request):
    """カメラの利用可能性をチェック"""
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'available_cameras': available_cameras,
            'camera_count': len(available_cameras),
            'message': f'{len(available_cameras)}個のカメラが利用可能です' if available_cameras else 'カメラが見つかりません'
        })
    else:
        return JsonResponse({'success': False, 'error': 'GETメソッドのみ対応'}, status=405)


@csrf_exempt
def test_camera_connection(request):
    """カメラ接続テスト"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            camera_index = data.get('camera_index', 0)
            
            from .applications.camera_get_data import VideoCamera
            import time
            
            # テスト用カメラを初期化
            test_camera = VideoCamera(src=camera_index, width=640, height=480)
            
            # 数フレーム取得してテスト
            test_results = []
            for i in range(5):
                frame_data = test_camera.get_jpeg()
                if frame_data:
                    test_results.append({
                        'frame': i + 1,
                        'success': True,
                        'size': len(frame_data)
                    })
                else:
                    test_results.append({
                        'frame': i + 1,
                        'success': False,
                        'size': 0
                    })
                time.sleep(0.2)
            
            test_camera.stop()
            
            success_count = sum(1 for result in test_results if result['success'])
            
            return JsonResponse({
                'success': True,
                'camera_index': camera_index,
                'test_results': test_results,
                'success_rate': f'{success_count}/5',
                'message': f'カメラ {camera_index} のテスト完了'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'カメラテストエラー: {str(e)}',
                'camera_index': camera_index if 'camera_index' in locals() else 'unknown'
            })
    else:
        return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'}, status=405)



