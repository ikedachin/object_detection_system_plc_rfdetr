from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
import os
import json
from pathlib import Path
from PIL import Image, ImageOps
import tempfile
import zipfile
from datetime import datetime
import yaml

from annotator.models import Project
from .models import CropSession, CropImage, CropArea, CropProgress, CropTemplate


@csrf_exempt
def crop_and_save_all(request):
    """プロジェクト内の全画像を指定bboxで切り抜き、croppedフォルダに保存"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POSTメソッドのみ対応しています。'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        project_id = data.get('project_id')
        folder_path = data.get('folder_path')
        bbox = data.get('bounding_box')
        print(f"[DEBUG {__name__} {crop_and_save_all.__name__}] Received data: project_id={project_id}, folder_path={folder_path}, bbox={bbox}")
        if not (project_id and folder_path and bbox):
            return JsonResponse({'success': False, 'message': '必要なデータが不足しています。'})

        # プロジェクト取得
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({'success': False, 'message': '指定されたプロジェクトが存在しません。'})

        # プロジェクトディレクトリの絶対パスを構築
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        project_dir = os.path.join(base_dir, 'projects', str(project.folder_name))
        abs_folder = os.path.join(project_dir, folder_path)
        if not os.path.exists(abs_folder):
            return JsonResponse({'success': False, 'message': f'フォルダが存在しません: {abs_folder}'})
        print(f"[DEBUG {__name__} {crop_and_save_all.__name__}] Absolute folder path: {abs_folder}")
        # croppedフォルダ作成
        cropped_dir = os.path.join(os.path.dirname(abs_folder), 'cropped')
        os.makedirs(cropped_dir, exist_ok=True)

        # bbox情報
        x, y, w, h = int(bbox['x']), int(bbox['y']), int(bbox['width']), int(bbox['height'])

        # 画像ファイル一覧取得 (jpg, jpeg, png, bmp, gif)
        image_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.JPG', '.JPEG', '.PNG', '.BMP', '.GIF')
        files = [f for f in os.listdir(abs_folder) if f.lower().endswith(image_exts) and os.path.isfile(os.path.join(abs_folder, f))]
        if not files:
            return JsonResponse({'success': False, 'message': '画像ファイルが見つかりません。'})

        # --- DB記録用: セッション作成 ---
        from .models import CropSession, CropImage, CropArea
        from django.utils import timezone
        session_name = f"一括切り抜き_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        crop_session = CropSession.objects.create(
            project=project,
            session_name=session_name,
            source_folder='base_images',  # 一括切り抜きの場合はbase_images等でOK
            notes=f"crop_and_save_all一括切り抜き: folder={folder_path}, bbox={bbox}"
        )

        success_count = 0
        error_files = []

        for fname in files:
            try:
                img_path = os.path.join(abs_folder, fname)
                with Image.open(img_path) as im:
                    im = ImageOps.exif_transpose(im)
                    width, height = im.size
                    # bbox範囲でcrop
                    cropped = im.crop((x, y, x + w, y + h))
                    # 640x640にリサイズ
                    cropped = cropped.resize((640, 640), Image.LANCZOS)
                    save_path = os.path.join(cropped_dir, fname)
                    cropped.save(save_path)

                # --- DB記録 ---
                crop_image = CropImage.objects.create(
                    session=crop_session,
                    image_name=fname,
                    original_path=img_path,
                    width=width,
                    height=height,
                    is_processed=True
                )
                CropArea.objects.create(
                    crop_image=crop_image,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    label="global_bbox"
                )
                success_count += 1
            except Exception as e:
                error_files.append({'file': fname, 'error': str(e)})

        # 統計情報を更新
        crop_session.update_statistics()
        if hasattr(project, 'crop_app_progress'):
            project.crop_app_progress.update_progress()

        # プロジェクトのcroppedフラグをTrueにして保存
        project.cropped = True
        project.save()

        return JsonResponse({
            'success': True,
            'cropped_dir': cropped_dir,
            'success_count': success_count,
            'error_count': len(error_files),
            'error_files': error_files,
            'crop_session_id': crop_session.id,
            'crop_session_name': crop_session.session_name
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'サーバーエラー: {str(e)}'})
    

    


def crop_tool(request):
    """切り取りツールのメイン画面"""
    # アクティブなプロジェクトを取得
    active_project = Project.get_active_project()
    all_projects = Project.objects.all().order_by('-created_at')
    
    # セッション一覧
    sessions = []
    if active_project:
        sessions = CropSession.objects.filter(project=active_project).order_by('-created_at')
    
    context = {
        'active_project': active_project,
        'all_projects': all_projects,
        'sessions': sessions,
    }
    return render(request, 'crop_app/crop.html', context)




@csrf_exempt
def create_crop_session(request):
    """新しい切り取りセッションを作成"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_id = data.get('project_id')
            session_name = data.get('session_name')
            source_folder = data.get('source_folder', 'auto')
            notes = data.get('notes', '')
            
            if not project_id or not session_name:
                return JsonResponse({'success': False, 'error': 'プロジェクトIDとセッション名が必要です'})
            
            project = get_object_or_404(Project, id=project_id)
            
            # セッション作成
            session = CropSession.objects.create(
                project=project,
                session_name=session_name,
                source_folder=source_folder,
                notes=notes
            )
            
            # 統計情報を更新
            session.update_statistics()
            
            return JsonResponse({
                'success': True,
                'session_id': session.id,
                'session_name': session.session_name,
                'source_folder': session.source_folder,
                'total_images': session.total_images
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'})


@csrf_exempt
def get_session_images(request):
    """セッションの画像一覧を取得"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            
            if not session_id:
                return JsonResponse({'success': False, 'error': 'セッションIDが必要です'})
            
            session = get_object_or_404(CropSession, id=session_id)
            source_path = session.source_path
            
            if not source_path or not os.path.exists(source_path):
                return JsonResponse({'success': False, 'error': f'画像フォルダが存在しません: {source_path}'})
            
            image_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')
            files = []
            
            for f in os.listdir(source_path):
                if f.lower().endswith(image_exts):
                    files.append(f)
            
            files.sort()
            
            return JsonResponse({
                'success': True,
                'files': files,
                'source_path': source_path,
                'session_info': {
                    'id': session.id,
                    'name': session.session_name,
                    'project': session.project.name,
                    'source_folder': session.source_folder,
                    'total_images': session.total_images,
                    'processed_images': session.processed_images
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'})


@csrf_exempt
def add_crop_image(request):
    """セッションに画像を追加"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            image_name = data.get('image_name')
            
            if not session_id or not image_name:
                return JsonResponse({'success': False, 'error': 'セッションIDと画像名が必要です'})
            
            session = get_object_or_404(CropSession, id=session_id)
            
            # 画像が存在するかチェック
            image_path = os.path.join(session.source_path, image_name)
            if not os.path.exists(image_path):
                return JsonResponse({'success': False, 'error': f'画像ファイルが見つかりません: {image_name}'})
            
            # 画像のサイズを取得
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
            except Exception:
                width, height = 0, 0
            
            # CropImageを作成または取得
            crop_image, created = CropImage.objects.get_or_create(
                session=session,
                image_name=image_name,
                defaults={
                    'original_path': image_path,
                    'width': width,
                    'height': height
                }
            )
            print(f"[DEBUG {__name__} {add_crop_image.__name__}] CropImage created: {created}, ID: {crop_image.id}")
            return JsonResponse({
                'success': True,
                'crop_image_id': crop_image.id,
                'created': created,
                'width': crop_image.width,
                'height': crop_image.height
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    print(f"[DEBUG {__name__} {add_crop_image.__name__}] Method not allowed: Only POST is supported")
    return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'})


@csrf_exempt
def save_crop_area(request):
    """切り取り領域を保存"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            crop_image_id = data.get('crop_image_id')
            x = data.get('x')
            y = data.get('y')
            width = data.get('width')
            height = data.get('height')
            label = data.get('label', '')
            
            if not all([crop_image_id is not None, x is not None, y is not None, width is not None, height is not None]):
                return JsonResponse({'success': False, 'error': '必要なパラメータが不足しています'})
            
            crop_image = get_object_or_404(CropImage, id=crop_image_id)
            
            # 切り取り領域を作成
            crop_area = CropArea.objects.create(
                crop_image=crop_image,
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                label=label
            )
            
            # 切り取り画像を保存
            cropped_path = crop_area.save_cropped_image()
            
            # 画像の処理状態を更新
            crop_image.is_processed = True
            crop_image.save()
            
            # セッションの統計を更新
            crop_image.session.update_statistics()
            
            return JsonResponse({
                'success': True,
                'crop_area_id': crop_area.id,
                'cropped_path': cropped_path
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'})


@csrf_exempt
def get_project_sessions(request):
    """プロジェクトのセッション一覧を取得"""
    if request.method == 'GET':
        try:
            project_id = request.GET.get('project_id')
            
            if not project_id:
                return JsonResponse({'success': False, 'error': 'プロジェクトIDが必要です'})
            
            project = get_object_or_404(Project, id=project_id)
            sessions = CropSession.objects.filter(project=project).order_by('-created_at')
            
            session_list = []
            for session in sessions:
                session_list.append({
                    'id': session.id,
                    'name': session.session_name,
                    'source_folder': session.source_folder,
                    'total_images': session.total_images,
                    'processed_images': session.processed_images,
                    'progress_percentage': session.progress_percentage,
                    'is_completed': session.is_completed,
                    'created_at': session.created_at.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'sessions': session_list,
                'project_name': project.name
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'GETメソッドのみ対応'})


@csrf_exempt
def get_crop_templates(request):
    """プロジェクトの切り取りテンプレートを取得"""
    if request.method == 'GET':
        try:
            project_id = request.GET.get('project_id')
            
            if not project_id:
                return JsonResponse({'success': False, 'error': 'プロジェクトIDが必要です'})
            
            project = get_object_or_404(Project, id=project_id)
            templates = CropTemplate.objects.filter(project=project, is_active=True).order_by('template_name')
            
            template_list = []
            for template in templates:
                template_list.append({
                    'id': template.id,
                    'name': template.template_name,
                    'label': template.label,
                    'width': template.width,
                    'height': template.height,
                    'description': template.description
                })
            
            return JsonResponse({
                'success': True,
                'templates': template_list
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'GETメソッドのみ対応'})

# --- 画像切り抜きAPI ---
def process_crop(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            image_path = data.get('image_path')
            x = int(data.get('x', 0))
            y = int(data.get('y', 0))
            width = int(data.get('width', 0))
            height = int(data.get('height', 0))
            if not image_path:
                return JsonResponse({'success': False, 'error': '画像パスが指定されていません'})
            # 絶対パス化
            if image_path.startswith('/'):
                abs_path = Path(settings.BASE_DIR).parent / image_path.lstrip('/')
            else:
                abs_path = Path(settings.BASE_DIR).parent / image_path
            if not abs_path.exists():
                return JsonResponse({'success': False, 'error': f'画像ファイルが見つかりません: {abs_path}'})
            with Image.open(str(abs_path)) as img:
                img = ImageOps.exif_transpose(img)
                cropped = img.crop((x, y, x + width, y + height))
                final_image = cropped.resize((640, 640), Image.Resampling.LANCZOS)
                output_dir = Path(settings.BASE_DIR).parent / 'crop_preparation' / 'cropped'
                output_dir.mkdir(parents=True, exist_ok=True)
                output_filename = f'{Path(image_path).stem}_cropped_640x640.jpg'
                output_path = output_dir / output_filename
                final_image.save(str(output_path), 'JPEG', quality=95, exif=b'')
                download_url = f'/crop_preparation/cropped/{output_filename}'
                return JsonResponse({'success': True, 'download_url': download_url})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})

# --- 一括切り抜きAPI ---
def process_batch_crop(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            image_path = data.get('image_path')
            coordinates_list = data.get('coordinates')
            if not image_path or not coordinates_list:
                return JsonResponse({'success': False, 'error': '画像パスまたは座標データが不足しています'})
            if image_path.startswith('/'):
                abs_path = Path(settings.BASE_DIR).parent / image_path.lstrip('/')
            else:
                abs_path = Path(settings.BASE_DIR).parent / image_path
            if not abs_path.exists():
                return JsonResponse({'success': False, 'error': f'画像ファイルが見つかりません: {abs_path}'})
            with Image.open(abs_path) as img:
                img = ImageOps.exif_transpose(img)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
                    zip_path = tmp_zip.name
                
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for i, coord in enumerate(coordinates_list):
                            try:
                                x = int(coord['x'])
                                y = int(coord['y'])
                                crop_box = (x, y, x + 640, y + 640)
                                cropped = img.crop(crop_box)
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_img:
                                    cropped.save(tmp_img.name, 'PNG', optimize=True)
                                    filename = f"crop_{i+1:03d}_x{x}_y{y}.png"
                                    zip_file.write(tmp_img.name, filename)
                                    os.unlink(tmp_img.name)
                            except Exception as crop_error:
                                continue
                    
                    with open(zip_path, 'rb') as zip_data:
                        response = HttpResponse(zip_data.read(), content_type='application/zip')
                        response['Content-Disposition'] = f"attachment; filename=\"batch_crop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip\""
                        return response
                finally:
                    # 一時ファイルを確実にクリーンアップ
                    if os.path.exists(zip_path):
                        os.unlink(zip_path)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})

# --- YAML保存API ---
def save_bounding_box_yaml(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            bounding_box = data.get('bounding_box')
            coordinates = data.get('individual_coordinates')
            if not bounding_box:
                return JsonResponse({'success': False, 'error': '必要なデータが不足しています'})
            yaml_dir = Path(settings.BASE_DIR).parent / 'settings'
            yaml_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            yaml_filename = f"bounding_box_{timestamp}.yaml"
            yaml_path = yaml_dir / yaml_filename
            yaml_data = {
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                },
                'bounding_box': {
                    'description': 'すべての切り抜き座標を包括する最小矩形',
                    'x': bounding_box['x'],
                    'y': bounding_box['y'],
                    'width': bounding_box['width'],
                    'height': bounding_box['height'],
                    'right': bounding_box['right'],
                    'bottom': bounding_box['bottom']
                },
                'individual_coordinates': [
                    {
                        'id': coord['id'],
                        'x': coord['x'],
                        'y': coord['y'],
                        'width': coord['width'],
                        'height': coord['height'],
                        'filename': coord.get('fileName', '不明')
                    }
                    for coord in coordinates
                ]
            }
            with open(yaml_path, 'w', encoding='utf-8') as yaml_file:
                yaml.dump(yaml_data, yaml_file, default_flow_style=False, allow_unicode=True, indent=2)
            return JsonResponse({'success': True, 'filename': yaml_filename, 'path': str(yaml_path)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})

def upload_image(request):
    """
    画像アップロードAPI
    """
    if request.method == 'POST':
        try:
            if 'image' not in request.FILES:
                return JsonResponse({'success': False, 'error': '画像ファイルが選択されていません'})
            
            uploaded_file = request.FILES['image']
            if not uploaded_file.content_type.startswith('image/'):
                return JsonResponse({'success': False, 'error': '画像ファイルではありません'})
            
            # アップロード先ディレクトリを作成
            upload_dir = Path(settings.BASE_DIR).parent / 'uploaded_images'
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # ファイル名の重複を避けるためタイムスタンプを追加
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{uploaded_file.name}"
            file_path = upload_dir / filename
            
            # ファイルを保存
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # 相対パスを返す
            relative_path = f'uploaded_images/{filename}'
            return JsonResponse({
                'success': True, 
                'filename': filename,
                'path': relative_path,
                'url': f'/{relative_path}'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})

@csrf_exempt
def process_global_bbox_crop(request):
    """包括座標での全画像を切り抜き - JSON形式でサーバー保存結果を返す"""
    print('cripping in crop_app.views.process_global_bbox_crop', request.method)
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            crop_requests = data.get('crop_requests', [])
            global_bounding_box = data.get('global_bounding_box')
            project_id = data.get('project_id')
            resize_to_640x640 = data.get('resize_to_640x640', True)
            save_mode = data.get('save_mode', 'server')  # 保存モード
            save_to_cropped_folder = data.get('save_to_cropped_folder', True)
            
            if not crop_requests or not global_bounding_box:
                return JsonResponse({'success': False, 'error': '切り抜きデータがありません'})
            
            if not project_id or project_id == 'default':
                return JsonResponse({'success': False, 'error': 'プロジェクトIDが必要です'})
            
            # プロジェクトルートディレクトリ
            project_root = settings.BASE_DIR.parent
            
            # プロジェクトを取得
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return JsonResponse({'success': False, 'error': '指定されたプロジェクトが存在しません'})
            
            # 出力先ディレクトリ（プロジェクトフォルダのcroppedフォルダ）
            if save_to_cropped_folder:
                output_dir = project_root / 'projects' / project.folder_name / 'cropped'
            else:
                output_dir = project_root / 'crop_preparation' / 'cropped'
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            success_count = 0
            error_count = 0
            error_messages = []
            saved_files = []
            
            for crop_request in crop_requests:
                try:
                    image_path = crop_request.get('image_path')
                    crop_data = crop_request.get('crop_data', global_bounding_box)
                    
                    # 画像パスの正規化（プロジェクトルートからの相対パス）
                    if image_path.startswith('./'):
                        image_path = image_path[2:]  # "./" を削除
                    elif image_path.startswith('/'):
                        image_path = image_path[1:]  # 先頭の "/" を削除
                    
                    full_image_path = project_root / image_path
                    
                    if not full_image_path.exists():
                        error_messages.append(f"画像が見つかりません: {image_path}")
                        error_count += 1
                        continue
                    
                    # 画像を開く
                    with Image.open(full_image_path) as img:
                        # RGB形式に変換（PNGの透明度を避けるため）
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # 包括座標で切り抜き
                        x = int(crop_data['x'])
                        y = int(crop_data['y'])
                        width = int(crop_data['width'])
                        height = int(crop_data['height'])
                        
                        # 正方形に調整（長辺を基準にする）
                        size = max(width, height)
                        
                        # 中心を維持して正方形にする
                        center_x = x + width // 2
                        center_y = y + height // 2
                        half_size = size // 2
                        
                        square_x = center_x - half_size
                        square_y = center_y - half_size
                        
                        # 画像境界内に座標を制限
                        square_x = max(0, min(square_x, img.width - size))
                        square_y = max(0, min(square_y, img.height - size))
                        
                        # 画像境界を超える場合はサイズを調整
                        if square_x + size > img.width:
                            size = img.width - square_x
                        if square_y + size > img.height:
                            size = img.height - square_y
                        
                        # 最終的な正方形の座標
                        final_x = max(0, square_x)
                        final_y = max(0, square_y)
                        final_size = min(size, img.width - final_x, img.height - final_y)
                        
                        # 切り抜き実行（正方形）
                        crop_box = (final_x, final_y, final_x + final_size, final_y + final_size)
                        cropped = img.crop(crop_box)
                        
                        # 正方形切り抜き後のリサイズ（640x640）
                        if resize_to_640x640:
                            # 既に正方形なので、640x640にリサイズ
                            cropped = cropped.resize((640, 640), Image.Resampling.LANCZOS)
                        
                        # ファイル名生成
                        original_filename = Path(image_path).stem
                        output_filename = f"global_bbox_{original_filename}.png"
                        
                        # プロジェクトのcroppedフォルダに保存
                        output_path = output_dir / output_filename
                        cropped.save(output_path, 'PNG', optimize=True)
                        
                        saved_files.append(str(output_path))
                        success_count += 1
                        
                except Exception as e:
                    error_messages.append(f"画像処理エラー ({Path(image_path).name}): {str(e)}")
                    error_count += 1
                    continue
            
            # 1件以上成功した場合はcroppedフラグを立てる
            if success_count > 0:
                project.cropped = True
                project.save(update_fields=["cropped"])

            # JSON形式でレスポンスを返す
            return JsonResponse({
                'success': True,
                'success_count': success_count,
                'error_count': error_count,
                'save_path': str(output_dir),
                'saved_files': saved_files,
                'errors': error_messages,
                'project_name': project.name,
                'resize_applied': resize_to_640x640
            })
                    
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'処理中にエラーが発生しました: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'POSTメソッドのみ対応'})

@csrf_exempt
def get_projects_list(request):
    """プロジェクト一覧を取得"""
    if request.method == 'GET':
        try:
            projects = Project.objects.all().order_by('-created_at')
            projects_data = []
            
            for project in projects:
                project_info = {
                    'id': project.id,
                    'name': project.name,
                    'description': '',  # Projectモデルにdescriptionフィールドがないので空文字列
                    'created_at': project.created_at.strftime('%Y-%m-%d %H:%M'),
                    'is_active': project.is_active,
                    'image_count': project.get_image_count() if hasattr(project, 'get_image_count') else 0,
                    'folders': []
                }
                
                # プロジェクトフォルダ内のサブフォルダを取得
                project_path = project.get_project_path()
                print(f"[DEBUG {__name__} {get_projects_list.__name__}] Project path: {project_path}")
                if project_path and os.path.exists(project_path):
                    try:
                        for item in os.listdir(project_path):
                            item_path = os.path.join(project_path, item)
                            if os.path.isdir(item_path) and not item.startswith('.'):
                                # フォルダ内の画像数をカウント
                                image_count = count_images_in_folder(item_path)
                                project_info['folders'].append({
                                    'name': item,
                                    'path': item_path,
                                    'image_count': image_count
                                })
                    except Exception as e:
                        print(f"プロジェクトフォルダ読み込みエラー: {e}")
                
                projects_data.append(project_info)
            
            return JsonResponse({
                'success': True,
                'projects': projects_data
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'GETメソッドのみ対応'})


@csrf_exempt
def get_project_folders(request):
    """
    指定プロジェクトのフォルダ一覧を取得（統合版）
    POST: { project_id: <id> } または
    GET: 全プロジェクトの詳細フォルダ情報を取得
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f'[DEBUG {__name__} {get_project_folders.__name__}] get_project_folders POST data:', data)
            project_id = data.get('project_id')
            
            if not project_id:
                return JsonResponse({'success': False, 'error': 'プロジェクトIDが必要です'})
            
            project = get_object_or_404(Project, id=project_id)
            project_path = project.get_project_path()
            
            folders = []
            if project_path and os.path.exists(project_path):
                for item in os.listdir(project_path):
                    item_path = os.path.join(project_path, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        image_count = count_images_in_folder(item_path)
                        folders.append({
                            'name': item,
                            'path': item_path,
                            'image_count': image_count
                        })
            print(f"[DEBUG {__name__} {get_project_folders.__name__}] Folders for project {project.name}: {folders}")
            print(f"[DEBUG {__name__} {get_project_folders.__name__}] Project id: {project.id}, name: {project.name}, path: {project_path}")

            return JsonResponse({
                'success': True,
                'project': {
                    'id': project.id,
                    'name': project.name,
                    'description': '',  # descriptionフィールドは存在しないため空文字列
                    'path': project_path
                },
                'folders': folders
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    elif request.method == 'GET':
        # 既存のget_project_image_folders機能を統合
        try:
            base_path = Path(settings.BASE_DIR).parent
            folders = {}
            
            # データベースからプロジェクトを取得
            projects = Project.objects.all().order_by('name')
            
            for project in projects:
                # プロジェクトの新構造パスを取得
                project_root = base_path / 'projects' / project.folder_name
                data_collection_path = project_root / 'data_collection'
                cropped_path = project_root / 'cropped'
                
                project_key = f"project_{project.id}"
                folders[project_key] = {
                    'name': project.name,
                    'subfolders': [],
                    'default_path': None  # デフォルトで使用するパス
                }
                
                # data_collectionフォルダが存在する場合
                if data_collection_path.exists():
                    image_count = count_images_in_folder(data_collection_path)
                    folder_data = {
                        'name': 'データ収集',
                        'path': f'projects/{project.folder_name}/data_collection',
                        'image_count': image_count
                    }
                    folders[project_key]['subfolders'].append(folder_data)
                    
                    # 画像が存在する場合は、data_collectionをデフォルトパスとして設定
                    if image_count > 0 and folders[project_key]['default_path'] is None:
                        folders[project_key]['default_path'] = folder_data['path']
                
                # croppedフォルダが存在する場合
                if cropped_path.exists():
                    image_count = count_images_in_folder(cropped_path)
                    folder_data = {
                        'name': '切り取り済み',
                        'path': f'projects/{project.folder_name}/cropped',
                        'image_count': image_count
                    }
                    folders[project_key]['subfolders'].append(folder_data)
                    
                    # まだデフォルトパスが設定されていない場合は、croppedを使用
                    if folders[project_key]['default_path'] is None:
                        folders[project_key]['default_path'] = folder_data['path']
                        
                # デフォルトパスが設定されていない場合は最初のフォルダを使用
                if (folders[project_key]['default_path'] is None and 
                    folders[project_key]['subfolders']):
                    folders[project_key]['default_path'] = folders[project_key]['subfolders'][0]['path']
            
            return JsonResponse({'success': True, 'folders': folders})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTまたはGETメソッドのみ対応'})


@csrf_exempt
def browse_images(request):
    """
    画像フォルダ参照API（統合版）
    POST: { path: <dir_path> }
    既存機能と新機能を統合し、詳細情報も提供
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"[DEBUG {__name__} {browse_images.__name__}] browse_images POST data: {data}")
            folder_path = data.get('path')
            
            if not folder_path:
                return JsonResponse({'success': False, 'error': 'パスが指定されていません'})

            print(f"[DEBUG {__name__} {browse_images.__name__}] Requested folder_path: {folder_path}")
            abs_path = Path(folder_path.rstrip('/'))
            # # 絶対パス化
            # if folder_path.startswith('/'):
            #     abs_path = Path(settings.BASE_DIR).parent / folder_path.lstrip('/')
            # else:
            #     abs_path = Path(folder_path)  os.path.isabs(folder_path) else Path(settings.BASE_DIR).parent / folder_path

            print(f"[DEBUG {__name__} {browse_images.__name__}] Resolved abs_path: {abs_path}")
            print(f"[DEBUG {__name__} {browse_images.__name__}] Path exists: {abs_path.exists()}")
            print(f"[DEBUG {__name__} {browse_images.__name__}] Is directory: {abs_path.is_dir()}")

            # # パスが存在しない場合の代替パス試行
            # if not abs_path.exists() or not abs_path.is_dir():
            #     alternative_paths = [
            #         Path(settings.BASE_DIR).parent / 'base_images',
            #         Path(settings.BASE_DIR).parent / 'data_collection',
            #         settings.DATA_COLLECTION_DIR if hasattr(settings, 'DATA_COLLECTION_DIR') else None,
            #         settings.BASE_IMAGES_DIR if hasattr(settings, 'BASE_IMAGES_DIR') else None,
            #     ]
                
            #     print(f"[DEBUG] Trying alternative paths: {alternative_paths}")
                
            #     for alt_path in alternative_paths:
            #         if alt_path and alt_path.exists() and alt_path.is_dir():
            #             print(f"[DEBUG] Using alternative path: {alt_path}")
            #             abs_path = alt_path
            #             break
            #     else:
            #         return JsonResponse({'success': False, 'error': f'フォルダが存在しません: {abs_path}'})
            
            # 画像ファイルを検索
            image_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')
            files = []
            file_details = []
            
            try:
                for f in os.listdir(abs_path):
                    if f.lower().endswith(image_exts):
                        file_path = abs_path / f
                        files.append(f)
                        
                        # 画像の詳細情報を取得
                        try:
                            with Image.open(file_path) as img:
                                width, height = img.size
                            file_details.append({
                                'name': f,
                                'path': str(file_path),
                                'width': width,
                                'height': height
                            })
                        except Exception:
                            file_details.append({
                                'name': f,
                                'path': str(file_path),
                                'width': 0,
                                'height': 0
                            })
                        
                print(f"[DEBUG {__name__} {browse_images.__name__}] Found {len(files)} image files")
                print(f"[DEBUG {__name__} {browse_images.__name__}] Sample files: {files[:5]}")  # 最初の5個だけ表示

            except Exception as e:
                print(f"[DEBUG {__name__} {browse_images.__name__}] Error listing directory: {e}")
                return JsonResponse({'success': False, 'error': f'ディレクトリの読み込みエラー: {e}'})
            
            # ファイル名でソート
            files.sort()
            file_details.sort(key=lambda x: x['name'])
            
            return JsonResponse({
                'success': True, 
                'files': files,  # 互換性のため名前のみのリスト
                'file_details': file_details,  # 詳細情報
                'path': str(abs_path),
                'total_count': len(files),
                'debug_info': {
                    'requested_path': folder_path,
                    'resolved_path': str(abs_path),
                    'file_count': len(files)
                }
            })
            
        except Exception as e:
            print(f"[DEBUG {__name__} {browse_images.__name__}] Exception in browse_images: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})


def count_images_in_folder(folder_path):
    """
    フォルダ内の画像ファイル数をカウント（統合版）
    Path オブジェクトと文字列パスの両方をサポート
    """
    if isinstance(folder_path, str):
        if not os.path.exists(folder_path):
            return 0
        path_obj = Path(folder_path)
    else:
        path_obj = folder_path
        if not path_obj.exists():
            return 0
    
    image_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')
    count = 0
    
    try:
        if isinstance(folder_path, str):
            # 文字列パスの場合はos.listdirを使用
            for f in os.listdir(folder_path):
                if f.lower().endswith(image_exts):
                    count += 1
        else:
            # Pathオブジェクトの場合はiterdirを使用
            for file in path_obj.iterdir():
                if file.is_file() and file.suffix.lower() in image_exts:
                    count += 1
    except Exception:
        return 0
    
    return count


def get_project_image(request):
    if request.method == 'GET':
        try:
            project_name = request.GET.get('project')
            folder_name = request.GET.get('folder')
            image_name = request.GET.get('image')

            if not project_name or not folder_name or not image_name:
                return JsonResponse({'success': False, 'error': '必要なパラメータが不足しています'}, status=400)

            project = get_object_or_404(Project, name=project_name)
            project_path = Path(project.get_project_path())
            image_path = project_path / folder_name / image_name

            if not image_path.exists():
                return JsonResponse({'success': False, 'error': '画像が見つかりません'}, status=404)

            ext = image_path.suffix.lower()
            content_type = 'image/jpeg'
            if ext == '.png':
                content_type = 'image/png'
            elif ext == '.gif':
                content_type = 'image/gif'

            with open(image_path, 'rb') as img_file:
                return HttpResponse(img_file.read(), content_type=content_type)

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'GETメソッドのみ対応'}, status=405)