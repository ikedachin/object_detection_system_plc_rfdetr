# views.py
import os
import json
import shutil
import datetime
from pathlib import Path

from PIL import Image, ImageOps
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.db import models, transaction

# Create your views here.

def configuration(request):
    return render(request, 'configuration.html')

def parse_json_request(request):
    """
    リクエストボディからJSONを安全に解析する共通関数
    """
    try:
        print(f"parse_json_request: request.body = {request.body}")  # デバッグ用
        print(f"parse_json_request: request.body type = {type(request.body)}")  # デバッグ用
        
        if not request.body:
            print("parse_json_request: Request body is empty")  # デバッグ用
            return None, 'リクエストボディが空です'
        
        # バイト文字列をデコード
        body_str = request.body.decode('utf-8')
        print(f"parse_json_request: decoded body = {body_str}")  # デバッグ用
        
        if not body_str.strip():
            print("parse_json_request: Decoded body is empty")  # デバッグ用
            return None, 'リクエストボディが空です'
        
        data = json.loads(body_str)
        print(f"parse_json_request: parsed data = {data}")  # デバッグ用
        return data, None
        
    except json.JSONDecodeError as e:
        print(f"parse_json_request: JSON decode error = {e}")  # デバッグ用
        return None, f'JSONデータの解析に失敗しました: {str(e)}'
    except UnicodeDecodeError as e:
        print(f"parse_json_request: Unicode decode error = {e}")  # デバッグ用
        return None, f'文字エンコーディングエラー: {str(e)}'
    except Exception as e:
        print(f"parse_json_request: Unexpected error = {e}")  # デバッグ用
        return None, f'予期しないエラー: {str(e)}'

# def crop_image_view(request, image_id=None):
#     """画像切り抜きビュー"""
#     # プロジェクトルート（manage.pyがある階層）を基準とする
#     project_root = settings.BASE_DIR.parent
    
#     # デフォルト画像パスまたは指定された画像
#     if image_id:
#         image_url = f"/snaps/snaps_auto/{image_id}.jpg"
#     else:
#         # デフォルト画像またはsnaps_autoから最初の画像を使用
#         search_path = project_root / 'snaps' / 'snaps_auto'
        
#         if not search_path.exists():
#             # ディレクトリが存在しない場合は空のURLを返す
#             image_url = ""
#             image_id = "default"
#         else:
#             default_files = []
#             for ext in ['*.jpg', '*.jpeg', '*.png']:
#                 files = list(search_path.glob(ext))
#                 default_files.extend(files)
            
#             if default_files:
#                 # 最初のファイルを使用
#                 image_path = default_files[0]
#                 # プロジェクトルートからの相対パスに変換
#                 relative_path = image_path.relative_to(project_root)
#                 image_url = f"/{relative_path.as_posix()}"
#                 image_id = image_path.stem
#             else:
#                 # デフォルト画像がない場合
#                 image_url = ""
#                 image_id = "default"
    
#     return render(request, 'crop.html', {
#         'image_url': image_url,
#         'image_id': image_id
#     })



# def process_crop(request):
#     """画像切り抜き処理"""
#     print("Processing crop request...", request.method)
    
#     if request.method == 'POST':
#         # 共通のJSON解析関数を使用
#         data, error = parse_json_request(request)
#         if error:
#             return JsonResponse({
#                 'success': False,
#                 'error': error
#             })
        
#         try:
#             image_id = data['image_id']
#             x = data['x']
#             y = data['y']
#             width = data['width'] 
#             height = data['height']
            
#             # プロジェクトルート（manage.pyがある階層）を基準とする
#             project_root = settings.BASE_DIR.parent
            
#             # 共通の画像検索関数を使用
#             source_path = find_image_in_task_folders(image_id)
            
#             print(f"Searching for image: {image_id}")
#             print(f"Project root: {project_root}")
            
#             if not source_path:
#                 return JsonResponse({
#                     'success': False,
#                     'error': f'画像ファイルが見つかりません: {image_id}'
#                 })
            
#             print(f"Found image at: {source_path}")
            
#             # 切り抜き処理
#             with Image.open(str(source_path)) as img:
#                 # EXIF情報に基づいて画像の向きを修正
#                 img = correct_image_orientation(img)
                
#                 # 指定位置を切り抜き
#                 cropped = img.crop((x, y, x + width, y + height))
                
#                 # 640×640にリサイズ（高品質）
#                 final_image = cropped.resize((640, 640), Image.Resampling.LANCZOS)
                
#                 # 保存先ディレクトリを確保（新フォルダ構成）
#                 output_dir = settings.CROP_PREPARATION_CROPPED_DIR
#                 output_dir.mkdir(parents=True, exist_ok=True)
                
#                 # 保存（EXIFデータを除去して保存）
#                 output_filename = f'{image_id}_cropped_640x640.jpg'
#                 output_path = output_dir / output_filename
#                 final_image.save(str(output_path), 'JPEG', quality=95, exif=b'')
                
#                 # URLパスを新フォルダ構成に対応させる
#                 download_url = f'/crop_preparation/cropped/{output_filename}'
                
#                 return JsonResponse({
#                     'success': True,
#                     'download_url': download_url
#                 })
                
#         except Exception as e:
#             print(f"Error processing crop: {str(e)}")
#             return JsonResponse({
#                 'success': False,
#                 'error': str(e)
#             })
    
#     return JsonResponse({'success': False, 'error': 'Invalid request'})


# def process_batch_crop(request):
#     """
#     蓄積された複数の座標で一括切り抜きを実行し、ZIPファイルで返す
#     """
#     if request.method == 'POST':
#         try:
#             import zipfile
#             import tempfile
#             from django.http import HttpResponse
#             from datetime import datetime
            
#             # 共通のJSON解析関数を使用
#             data, error = parse_json_request(request)
#             if error:
#                 return JsonResponse({
#                     'success': False,
#                     'error': error
#                 })
            
#             image_path = data.get('image_path')
#             coordinates_list = data.get('coordinates')
            
#             if not image_path or not coordinates_list:
#                 return JsonResponse({'success': False, 'error': '画像パスまたは座標データが不足しています'})
            
#             # プロジェクトルート（manage.pyがある階層）を基準とする
#             project_root = settings.BASE_DIR.parent
            
#             # 画像パスを解決
#             if image_path.startswith('/snaps/'):
#                 # 静的ファイルパスから実際のファイルパスに変換
#                 relative_path = image_path.lstrip('/')
#                 full_image_path = project_root / relative_path
#             else:
#                 # 絶対パスまたは相対パス
#                 full_image_path = Path(image_path)
#                 if not full_image_path.is_absolute():
#                     full_image_path = project_root / image_path
            
#             print(f"Processing batch crop for image: {full_image_path}")
#             print(f"Number of coordinates: {len(coordinates_list)}")
            
#             if not full_image_path.exists():
#                 return JsonResponse({'success': False, 'error': f'画像ファイルが見つかりません: {full_image_path}'})
            
#             # 元画像を開いて向きを修正
#             try:
#                 with Image.open(full_image_path) as img:
#                     img = correct_image_orientation(img)
                    
#                     # 一時的なZIPファイルを作成
#                     with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_zip:
#                         zip_path = tmp_zip.name
                    
#                     successful_crops = 0
#                     failed_crops = 0
                    
#                     with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
#                         for i, coord in enumerate(coordinates_list):
#                             try:
#                                 x = int(coord['x'])
#                                 y = int(coord['y'])
                                
#                                 # 切り抜き処理（640x640pxに固定）
#                                 crop_box = (x, y, x + 640, y + 640)
#                                 cropped = img.crop(crop_box)
                                
#                                 # 一時的なファイルに保存
#                                 with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_img:
#                                     # EXIFデータを除去して保存
#                                     cropped.save(tmp_img.name, 'PNG', optimize=True)
                                    
#                                     # ZIPに追加
#                                     filename = f"crop_{i+1:03d}_x{x}_y{y}.png"
#                                     zip_file.write(tmp_img.name, filename)
                                    
#                                     # 一時ファイルを削除
#                                     os.unlink(tmp_img.name)
                                    
#                                 successful_crops += 1
                                
#                             except Exception as crop_error:
#                                 print(f"Error processing crop {i+1}: {str(crop_error)}")
#                                 failed_crops += 1
#                                 continue
                    
#                     # ZIPファイルを読み込んでレスポンスとして返す
#                     with open(zip_path, 'rb') as zip_data:
#                         response = HttpResponse(zip_data.read(), content_type='application/zip')
                        
#                         # ファイル名を生成（タイムスタンプ付き）
#                         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#                         filename = f"batch_crop_{timestamp}_{successful_crops}items.zip"
#                         response['Content-Disposition'] = f'attachment; filename="{filename}"'
                        
#                         # 一時ファイルを削除
#                         os.unlink(zip_path)
                        
#                         print(f"Batch crop completed: {successful_crops} successful, {failed_crops} failed")
                        
#                         return response
                        
#             except Exception as img_error:
#                 return JsonResponse({'success': False, 'error': f'画像処理エラー: {str(img_error)}'})
                
#         except Exception as e:
#             print(f"Error in process_batch_crop: {str(e)}")
#             return JsonResponse({'success': False, 'error': str(e)})
    
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})


def browse_images(request):
    """画像フォルダ参照ビュー - 新プロジェクト別フォルダ構成に対応"""
    project_root = settings.BASE_DIR.parent
    
    # 新プロジェクト別フォルダ構成のパス
    image_folders = {
        # デフォルトプロジェクトのフォルダ
        'default_data_collection': project_root / 'projects' / settings.DEFAULT_PROJECT_NAME / 'data_collection',
        'default_annotated_images': project_root / 'projects' / settings.DEFAULT_PROJECT_NAME / 'annotated' / 'images',
        'default_cropped': project_root / 'projects' / settings.DEFAULT_PROJECT_NAME / 'cropped',
        
        # 下位互換性のため従来フォルダも保持
        'legacy_annotation_data': getattr(settings, 'LEGACY_ANNOTATION_DATA_DIR', project_root / 'annotation_data' / 'images'),
        'legacy_data_collection': getattr(settings, 'LEGACY_DATA_COLLECTION_DIR', project_root / 'data_collection'),
        'legacy_base_images': project_root / 'base_images',
        'legacy_snaps_auto': project_root / 'snaps' / 'snaps_auto',
        'legacy_snaps_manual': project_root / 'snaps' / 'snaps_manual',
        'legacy_cropped': settings.MEDIA_ROOT / 'cropped' if hasattr(settings, 'MEDIA_ROOT') else project_root / 'media' / 'cropped'
    }
    
    # 各フォルダの画像数を取得
    folder_info = {}
    for folder_name, folder_path in image_folders.items():
        if folder_path.exists():
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
            image_files = [f for f in os.listdir(folder_path) 
                          if f.lower().endswith(image_extensions)]
            folder_info[folder_name] = {
                'path': str(folder_path),
                'count': len(image_files),
                'exists': True,
                'task_phase': get_task_phase_from_folder_name(folder_name)
            }
        else:
            folder_info[folder_name] = {
                'path': str(folder_path),
                'count': 0,
                'exists': False,
                'task_phase': get_task_phase_from_folder_name(folder_name)
            }
    
    return render(request, 'browse_images.html', {
        'folder_info': folder_info
    })


def get_task_phase_from_folder_name(folder_name):
    """
    フォルダ名からタスクフェーズを判定
    """
    if 'data_collection' in folder_name:
        return 'data_collection'
    elif 'crop' in folder_name:
        return 'crop_preparation'
    elif 'annotation' in folder_name:
        return 'annotation'
    elif 'training' in folder_name:
        return 'training'
    elif 'production' in folder_name:
        return 'production'
    else:
        return 'unknown'


# def correct_image_orientation(img):
#     """
#     EXIFデータに基づいて画像の向きを修正する
#     """
#     try:
#         # EXIFの向き情報を使用して画像を自動回転
#         img = ImageOps.exif_transpose(img)
#         return img
#     except Exception as e:
#         print(f"EXIF orientation correction failed: {str(e)}")
#         # エラーが発生した場合は元の画像をそのまま返す
#         return img


# def save_bounding_box_yaml(request):
#     """
#     包括座標をYAMLファイルに保存する
#     """
#     if request.method == 'POST':
#         try:
#             import yaml
#             from datetime import datetime
            
#             # 共通のJSON解析関数を使用
#             data, error = parse_json_request(request)
#             if error:
#                 return JsonResponse({
#                     'success': False,
#                     'error': error
#                 })
            
#             # image_path = data.get('image_path')
#             # image_filename = data.get('image_filename')
#             bounding_box = data.get('bounding_box')
#             coordinates = data.get('coordinates')
#             # total_coordinates = data.get('total_coordinates')
            
#             if not bounding_box:
#                 return JsonResponse({'success': False, 'error': '必要なデータが不足しています'})
#             # プロジェクトルート（manage.pyがある階層）を基準とする
#             project_root = settings.BASE_DIR.parent
            
#             # YAMLファイル保存先ディレクトリ
#             yaml_dir = project_root / 'settings'
#             yaml_dir.mkdir(exist_ok=True)
            
#             # ファイル名を生成（タイムスタンプ付き）
#             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#             # image_name_without_ext = os.path.splitext(image_filename)[0] if image_filename != '不明' else 'unknown'
#             yaml_filename = f"bounding_box_{timestamp}.yaml"
#             yaml_path = yaml_dir / yaml_filename

            
#             # YAML構造を作成
#             yaml_data = {
#                 'metadata': {
#                     'created_at': datetime.now().isoformat(),
#                     # 'image_file': image_filename,
#                     # 'image_path': image_path,
#                     # 'total_coordinates': total_coordinates
#                 },
#                 'bounding_box': {
#                     'description': 'すべての切り抜き座標を包括する最小矩形',
#                     'x': bounding_box['x'],
#                     'y': bounding_box['y'],
#                     'width': bounding_box['width'],
#                     'height': bounding_box['height'],
#                     'right': bounding_box['right'],
#                     'bottom': bounding_box['bottom']
#                 },
#                 'individual_coordinates': [
#                     {
#                         'id': coord['id'],
#                         'x': coord['x'],
#                         'y': coord['y'],
#                         'width': coord['width'],
#                         'height': coord['height'],
#                         'filename': coord.get('fileName', '不明')
#                     }
#                     for coord in coordinates
#                 ]
#             }
#             # print(f"YAML data to save: {yaml_data}")
#             # YAMLファイルに保存
#             with open(yaml_path, 'w', encoding='utf-8') as yaml_file:
#                 yaml.dump(yaml_data, yaml_file, default_flow_style=False, allow_unicode=True, indent=2)
            
#             # print(f"Bounding box YAML saved: {yaml_path}")
            
#             return JsonResponse({
#                 'success': True,
#                 'filename': yaml_filename,
#                 'path': str(yaml_path)
#             })
            
#         except Exception as e:
#             print(f"Error in save_bounding_box_yaml: {str(e)}")
#             return JsonResponse({'success': False, 'error': str(e)})
    
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})


# def save_global_bounding_box_yaml(request):
#     """全体包括座標をYAMLファイルに保存"""
#     if request.method == 'POST':
#         # 共通のJSON解析関数を使用
#         data, error = parse_json_request(request)
#         if error:
#             return JsonResponse({
#                 'success': False,
#                 'error': error
#             })
        
#         try:
#             global_bounding_box = data.get('global_bounding_box')
#             all_coordinates = data.get('all_coordinates', [])
            
#             if not global_bounding_box:
#                 return JsonResponse({'success': False, 'error': '包括座標データがありません'})
            
#             # プロジェクトルートディレクトリ
#             project_root = settings.BASE_DIR.parent
            
#             # YAMLファイル名を生成（タイムスタンプ付き）
#             from datetime import datetime
#             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#             yaml_filename = f'global_bounding_box_{timestamp}.yaml'
#             yaml_path = project_root / 'settings' / yaml_filename
            
#             # settingsディレクトリが存在しない場合は作成
#             os.makedirs(yaml_path.parent, exist_ok=True)
            
#             # YAML形式のデータを構築
#             import yaml
#             yaml_data = {
#                 'global_bounding_box': {
#                     'total_images': global_bounding_box['totalImages'],
#                     'total_coordinates': global_bounding_box['totalCoordinates'],
#                     'x': global_bounding_box['x'],
#                     'y': global_bounding_box['y'],
#                     'width': global_bounding_box['width'],
#                     'height': global_bounding_box['height'],
#                     'right': global_bounding_box['right'],
#                     'bottom': global_bounding_box['bottom']
#                 },
#                 'image_details': [
#                     {
#                         'image_path': detail['imagePath'],
#                         'filename': detail['fileName'],
#                         'coordinates_count': detail['coordinates'],
#                         'bounding_box': {
#                             'x': detail['x'],
#                             'y': detail['y'],
#                             'width': detail['width'],
#                             'height': detail['height'],
#                             'right': detail['right'],
#                             'bottom': detail['bottom']
#                         }
#                     }
#                     for detail in global_bounding_box.get('imageDetails', [])
#                 ],
#                 'all_coordinates': [
#                     {
#                         'image_path': coord.get('imagePath', ''),
#                         'x': coord['x'],
#                         'y': coord['y'],
#                         'width': coord['width'],
#                         'height': coord['height'],
#                         'filename': coord.get('fileName', '不明')
#                     }
#                     for coord in all_coordinates
#                 ],
#                 'creation_timestamp': datetime.now().isoformat()
#             }
            
#             # YAMLファイルに保存
#             with open(yaml_path, 'w', encoding='utf-8') as yaml_file:
#                 yaml.dump(yaml_data, yaml_file, default_flow_style=False, allow_unicode=True, indent=2)
            
#             print(f"Global bounding box YAML saved: {yaml_path}")
            
#             return JsonResponse({
#                 'success': True,
#                 'filename': yaml_filename,
#                 'path': str(yaml_path)
#             })
            
#         except Exception as e:
#             print(f"Error in save_global_bounding_box_yaml: {str(e)}")
#             return JsonResponse({'success': False, 'error': str(e)})
    
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})


# def export_global_bbox_crops(request):
#     """全体包括座標での一括切り抜き実行"""
#     print("Exporting global bounding box crops...", request.method)
#     if request.method == 'POST':
#         # 共通のJSON解析関数を使用
#         data, error = parse_json_request(request)
#         if error:
#             return JsonResponse({
#                 'success': False,
#                 'error': error
#             })
        
#         try:
#             crop_requests = data.get('crop_requests', [])
#             global_bounding_box = data.get('global_bounding_box')
            
#             if not crop_requests or not global_bounding_box:
#                 return JsonResponse({'success': False, 'error': '切り抜きデータがありません'})
            
#             # プロジェクトルートディレクトリ
#             project_root = settings.BASE_DIR.parent
            
#             # 一時ディレクトリを作成
#             import tempfile
#             import zipfile
#             from datetime import datetime
            
#             timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#             temp_dir = tempfile.mkdtemp()
#             zip_filename = f'global_bbox_crops_{timestamp}.zip'
#             zip_path = os.path.join(temp_dir, zip_filename)
            
#             with zipfile.ZipFile(zip_path, 'w') as zip_file:
#                 processed_count = 0
                
#                 for request_data in crop_requests:
#                     image_path = request_data['image_path']
#                     crop_data = request_data['crop_data']
                    
#                     # 画像ファイルの絶対パスを取得
#                     if image_path.startswith('/'):
#                         # 絶対パスから相対パスに変換
#                         relative_path = image_path.lstrip('/')
#                     else:
#                         relative_path = image_path
                    
#                     full_image_path = project_root / relative_path
                    
#                     if not full_image_path.exists():
#                         print(f"Image not found: {full_image_path}")
#                         continue
                    
#                     # 画像を読み込み
#                     try:
#                         image = Image.open(full_image_path)
                        
#                         # 切り抜き座標を取得
#                         x = crop_data['x']
#                         y = crop_data['y']
#                         width = crop_data['width']
#                         height = crop_data['height']
                        
#                         # 画像の境界をチェック
#                         img_width, img_height = image.size
#                         x = max(0, min(x, img_width))
#                         y = max(0, min(y, img_height))
#                         width = min(width, img_width - x)
#                         height = min(height, img_height - y)
                        
#                         if width <= 0 or height <= 0:
#                             print(f"Invalid crop dimensions for {image_path}")
#                             continue
                        
#                         # 切り抜き実行
#                         cropped = image.crop((x, y, x + width, y + height))
                        
#                         # 640x640にリサイズ
#                         resized = cropped.resize((640, 640), Image.Resampling.LANCZOS)
                        
#                         # ファイル名を生成
#                         base_name = os.path.splitext(os.path.basename(image_path))[0]
#                         output_filename = f"{base_name}_global_bbox_crop.png"
                        
#                         # ZIPファイルに追加
#                         import io
#                         img_buffer = io.BytesIO()
#                         resized.save(img_buffer, format='PNG')
#                         img_buffer.seek(0)
                        
#                         zip_file.writestr(output_filename, img_buffer.getvalue())
#                         processed_count += 1
                        
#                     except Exception as e:
#                         print(f"Error processing image {image_path}: {str(e)}")
#                         continue
                
#                 # 包括座標情報をテキストファイルとして追加
#                 info_text = f"""全体包括座標での一括切り抜き情報
# 作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# 対象画像数: {global_bounding_box['totalImages']}
# 総座標数: {global_bounding_box['totalCoordinates']}
# 全体包括座標: X={global_bounding_box['x']}, Y={global_bounding_box['y']}
# 全体サイズ: {global_bounding_box['width']} × {global_bounding_box['height']} px
# 処理済み画像数: {processed_count}

# """
#                 zip_file.writestr('crop_info.txt', info_text.encode('utf-8'))
            
#             # ZIPファイルを返す
#             from django.http import HttpResponse
#             with open(zip_path, 'rb') as zip_file:
#                 response = HttpResponse(zip_file.read(), content_type='application/zip')
#                 response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
                
#             # 一時ファイルを削除
#             os.unlink(zip_path)
#             os.rmdir(temp_dir)
            
#             return response
            
#         except Exception as e:
#             print(f"Error in export_global_bbox_crops: {str(e)}")
#             return JsonResponse({'success': False, 'error': str(e)})
    
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})


# def skip_crop_to_annotation(request):
#     """
#     切り抜きをスキップして画像を直接アノテーションフォルダに移動
#     """
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             image_ids = data.get('image_ids', [])
            
#             if not image_ids:
#                 return JsonResponse({
#                     'success': False,
#                     'error': '画像IDが見つかりません'
#                 })
            
#             moved_count = 0
#             failed_images = []
            
#             for image_id in image_ids:
#                 try:
#                     # 元画像を検索
#                     source_path = find_image_in_task_folders(image_id)
                    
#                     if not source_path:
#                         failed_images.append(f'{image_id}: 画像が見つかりません')
#                         continue
                    
#                     # アノテーション用フォルダに直接コピー
#                     annotation_dir = settings.ANNOTATION_IMAGES_DIR
#                     annotation_dir.mkdir(parents=True, exist_ok=True)
                    
#                     # ファイル名を維持してコピー
#                     dest_path = annotation_dir / source_path.name
                    
#                     if not dest_path.exists():
#                         import shutil
#                         shutil.copy2(source_path, dest_path)
#                         moved_count += 1
#                         print(f"Copied {source_path} to {dest_path}")
#                     else:
#                         print(f"File already exists: {dest_path}")
#                         moved_count += 1  # 既存でもカウント
                        
#                 except Exception as e:
#                     failed_images.append(f'{image_id}: {str(e)}')
#                     continue
            
#             return JsonResponse({
#                 'success': True,
#                 'moved_count': moved_count,
#                 'failed_images': failed_images,
#                 'message': f'{moved_count}枚の画像をアノテーション用フォルダに移動しました'
#             })
            
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': f'処理エラー: {str(e)}'
#             })
    
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})


# def find_image_in_task_folders(image_id):
#     """
#     タスクフォルダから画像を検索する共通関数
#     """
#     project_root = settings.BASE_DIR.parent
    
#     # 検索対象パス（優先順位順）
#     search_paths = [
#         # データ収集フォルダ
#         settings.DATA_COLLECTION_AUTO_DIR / f'{image_id}.jpg',
#         settings.DATA_COLLECTION_AUTO_DIR / f'{image_id}.jpeg',
#         settings.DATA_COLLECTION_AUTO_DIR / f'{image_id}.png',
#         settings.DATA_COLLECTION_MANUAL_DIR / f'{image_id}.jpg',
#         settings.DATA_COLLECTION_MANUAL_DIR / f'{image_id}.jpeg',
#         settings.DATA_COLLECTION_MANUAL_DIR / f'{image_id}.png',
        
#         # 切り抜き準備フォルダ
#         settings.CROP_PREPARATION_SOURCE_DIR / f'{image_id}.jpg',
#         settings.CROP_PREPARATION_SOURCE_DIR / f'{image_id}.jpeg',
#         settings.CROP_PREPARATION_SOURCE_DIR / f'{image_id}.png',
#         settings.CROP_PREPARATION_CROPPED_DIR / f'{image_id}.jpg',
#         settings.CROP_PREPARATION_CROPPED_DIR / f'{image_id}.jpeg',
#         settings.CROP_PREPARATION_CROPPED_DIR / f'{image_id}.png',
        
#         # 従来フォルダ（下位互換性）
#         project_root / 'base_images' / f'{image_id}.jpg',
#         project_root / 'base_images' / f'{image_id}.jpeg',
#         project_root / 'base_images' / f'{image_id}.png',
#         project_root / 'snaps' / 'snaps_auto' / f'{image_id}.jpg',
#         project_root / 'snaps' / 'snaps_auto' / f'{image_id}.jpeg',
#         project_root / 'snaps' / 'snaps_auto' / f'{image_id}.png',
#         project_root / 'snaps' / 'snaps_manual' / f'{image_id}.jpg',
#         project_root / 'snaps' / 'snaps_manual' / f'{image_id}.jpeg',
#         project_root / 'snaps' / 'snaps_manual' / f'{image_id}.png',
#     ]
    
#     for path in search_paths:
#         if path.exists():
#             return path
    
#     return None

def workflow_manager(request):
    """
    タスクワークフロー管理画面
    切り抜きの実施有無を選択できるインターフェース
    """
    try:
        print("workflow_manager view called")  # デバッグ用
        
        project_root = settings.BASE_DIR.parent
        
        # 各ステップのフォルダ情報を取得
        workflow_steps = {
            'data_collection': {
                'name': '1. データ収集',
            },
            'crop_preparation': {
                'name': '2. 画像切り抜き',
            },
            'annotation': {
                'name': '3. アノテーション',
            },
            'training': {
                'name': '4. 学習',
            },
            'production': {
                'name': '5. 員数確認',
            }
        }
        
        # 各フォルダの画像数を取得
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        
        # ワークフローオプション
        workflow_options = {
            'with_crop': {
                'name': '切り抜きありワークフロー',
                'description': 'データ収集 → 画像切り抜き → アノテーション → 学習 → 実用',
                'steps': ['data_collection', 'crop_preparation', 'annotation', 'training', 'production'],
                'icon': '🔄'
            },
            'without_crop': {
                'name': '切り抜きなしワークフロー',
                'description': 'データ収集 → アノテーション → 学習 → 実用',
                'steps': ['data_collection', 'annotation', 'training', 'production'],
                'icon': '⚡'
            }
        }
        
        # セッションから現在のワークフロータイプを取得（デフォルト: with_crop）
        current_workflow_type = request.session.get('workflow_type', 'with_crop')
        
        # 選択されたワークフロータイプに基づいてワークフローステップをフィルタリング
        active_workflow_steps = {}
        if current_workflow_type == 'without_crop':
            # 切り抜きなしワークフローの場合は、crop_preparationステップを除外
            for step_key, step_info in workflow_steps.items():
                if step_key != 'crop_preparation':
                    active_workflow_steps[step_key] = step_info
        else:
            # 切り抜きありワークフローの場合は、すべてのステップを含める
            active_workflow_steps = workflow_steps

        # print("Rendering workflow_manager template")  # デバッグ用
        # print(f"workflow_steps: {active_workflow_steps}")  # デバッグ用

        return render(request, 'configuration/workflow_manager.html', {
            'current_workflow_type': current_workflow_type,
            'workflow_options': workflow_options,
            'workflow_steps': active_workflow_steps
        })
        
    except Exception as e:
        print(f"Error in workflow_manager view: {e}")
        from django.http import HttpResponse
        return HttpResponse(f"Error: {e}", status=500)


def change_workflow(request):
    """
    ワークフロー変更処理
    """
    if request.method == 'POST':
        try:
            # Content-Typeに応じてデータを解析
            if 'application/json' in request.content_type:
                # JSON形式の場合
                data, error = parse_json_request(request)
                if error:
                    return JsonResponse({
                        'success': False,
                        'error': error
                    })
                workflow_type = data.get('workflow_type')
            elif 'application/x-www-form-urlencoded' in request.content_type:
                # フォーム形式の場合
                workflow_type = request.POST.get('workflow_type')
            else:
                # その他の場合はPOSTデータを試行
                workflow_type = request.POST.get('workflow_type')
            
            if workflow_type in ['with_crop', 'without_crop']:
                # セッションにワークフロータイプを保存
                request.session['workflow_type'] = workflow_type
                
                workflow_names = {
                    'with_crop': '切り抜きありワークフロー',
                    'without_crop': '切り抜きなしワークフロー'
                }
                
                return JsonResponse({
                    'success': True,
                    'message': f'{workflow_names[workflow_type]}に変更しました',
                    'workflow_type': workflow_type
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': '無効なワークフロータイプです'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'エラーが発生しました: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})



def crop_redirect(request):
    """
    切り抜きアプリへのリダイレクト
    """
    print("Redirecting to crop app...")  # デバッグ用
    from django.shortcuts import redirect
    return redirect('/crop/')


def project_manager(request):
    """プロジェクト管理ページ（DBのみ参照）"""
    # print("[project_manager] called (DB only)")
    try:
        # DBからプロジェクト情報のみ取得
        db_projects = []
        try:
            from annotator.models import Project
            # print("[project_manager] Project model imported")
            for project in Project.objects.all():
                # print(f"[project_manager] DB project: {project.folder_name}, is_active={project.is_active}")
                db_projects.append({
                    'id': project.id,
                    'name': project.name,
                    'folder_name': project.folder_name,
                    'is_active': project.is_active,
                    'created_at_db': project.created_at,
                    'save_path': str(project.save_path),
                    'image_count': project.get_image_count() if hasattr(project, 'get_image_count') else None
                })
        except ImportError:
            print("[project_manager] annotator.modelsがインポートできません")
        except Exception as e:
            print(f"[project_manager] データベースからのプロジェクト取得でエラー: {e}")

        context = {
            'page_title': 'プロジェクト管理',
            'projects': db_projects,
        }
        # print(f"[project_manager] context: {context}")
        return render(request, 'project_manager.html', context)
    except Exception as e:
        print(f"[project_manager] Error in project_manager view: {e}")
        from django.http import HttpResponse
        return HttpResponse(f"Error: {e}", status=500)


def add_project(request):
    """プロジェクト追加API (画像アップロード対応)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'})

    project_name = request.POST.get('project_name', '').strip()
    source_folder = request.POST.get('source_folder', '').strip()
    # print(f"add_project: project_name = {project_name}")  # デバッグ用
    # print(f"add_project: source_folder = {source_folder}")  # デバッグ用

    if not project_name:
        project_name = source_folder.split('/')[-1] if source_folder else ''
        print("add_project: プロジェクト名が空です")  # デバッグ用
        return JsonResponse({'success': False, 'error': 'フォルダ名をプロジェクト名としました'})
    if not source_folder:
        print("add_project: 元フォルダが空です")  # デバッグ用
        return JsonResponse({'success': False, 'error': '元フォルダのパスを選択してください'})
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    if any(char in project_name for char in invalid_chars):
        print(f"add_project: 無効な文字が含まれています: {project_name}")  # デバッグ用
        return JsonResponse({'success': False, 'error': f'プロジェクト名に無効な文字が含まれています: {", ".join(invalid_chars)}'})

    project_root = Path(settings.BASE_DIR.parent)
    projects_dir = project_root / 'projects'
    new_project_dir = projects_dir / project_name / 'data_collection'
    # print(f"add_project: projects_dir = {projects_dir}")  # デバッグ用
    # print(f"add_project: new_project_dir = {new_project_dir}")  # デバッグ用
    projects_dir.mkdir(parents=True, exist_ok=True)
    new_project_dir.mkdir(parents=True, exist_ok=True)

    # 画像ファイル保存処理
    image_files = request.FILES.getlist('images')
    copied_files = 0
    skipped_files = 0
    error_files = []
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp')
    # print(f"add_project: 画像ファイル保存開始 (アップロード数: {len(image_files)})")  # デバッグ用
    for img in image_files:
        # webkitRelativePathでサブフォルダ再現
        rel_path = img.name if hasattr(img, 'name') else None
        if hasattr(img, 'webkit_relative_path'):
            rel_path = img.webkit_relative_path
        # サブフォルダ再現
        target_path = new_project_dir / rel_path if rel_path else new_project_dir / img.name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(target_path, 'wb+') as f:
                for chunk in img.chunks():
                    f.write(chunk)
            if str(target_path).lower().endswith(image_extensions):
                copied_files += 1
            else:
                skipped_files += 1
        except Exception as file_error:
            print(f"add_project: ファイル保存エラー: {img.name} - {file_error}")  # デバッグ用
            error_files.append(f"{img.name}: {str(file_error)}")
            if len(error_files) > 10:
                break
    # print(f"add_project: 画像保存完了 - 画像: {copied_files}, その他: {skipped_files}, エラー: {len(error_files)}")  # デバッグ用

    # データベース登録
    try:
        from annotator.models import Project
        if Project.objects.filter(name=project_name).exists():
            print(f"add_project: データベースに同名のプロジェクトが既に存在: {project_name}")  # デバッグ用
        elif Project.objects.filter(folder_name=project_name).exists():
            print(f"add_project: データベースに同じフォルダ名のプロジェクトが既に存在: {project_name}")  # デバッグ用
        else:
            project_db = Project.objects.create(
                name=project_name,
                folder_name=project_name,
                is_active=False,
                cropped=False,
                save_path=str(new_project_dir.parent.relative_to(project_root)).replace(os.path.sep, '/'),  # 画像保存先パスをDBに保存
            )
            # project_dbをアクティブなプロジェクトに変更する。（Project.set_avtive関数を用いる）
            project_db.set_active()
            # print(f"add_project: データベースにプロジェクトを保存: {project_db}")  # デバッグ用
    except ImportError as import_error:
        print(f"add_project: annotator.modelsのインポートに失敗: {import_error}")  # デバッグ用
    except Exception as db_error:
        print(f"add_project: データベース保存でエラー: {db_error}")  # デバッグ用
    result = {
        'success': True,
        'message': f'プロジェクト "{project_name}" を正常に作成しました',
        'copied_files': copied_files,
        'skipped_files': skipped_files,
        'project_path': str(new_project_dir)
    }
    return JsonResponse(result)


def delete_project(request):
    """プロジェクト削除API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'})
    
    try:
        data, error = parse_json_request(request)
        if error:
            return JsonResponse({'success': False, 'error': error})
        
        project_name = data.get('project_name', '').strip()
        
        if not project_name:
            return JsonResponse({'success': False, 'error': 'プロジェクト名を指定してください'})
        
        project_root = settings.BASE_DIR.parent
        projects_dir = project_root / 'projects'
        project_dir = projects_dir / project_name
        
        # プロジェクトディレクトリが存在するかチェック
        if not project_dir.exists():
            return JsonResponse({'success': False, 'error': f'プロジェクト "{project_name}" が見つかりません'})
        
        if not project_dir.is_dir():
            return JsonResponse({'success': False, 'error': f'指定されたパスはフォルダではありません: {project_name}'})
        
        # データベース削除をトランザクション内で実行
        deleted_db_records = 0
        try:
            with transaction.atomic():
                from annotator.models import Project, ImageFile, Annotation, Label
                from checker.models import Result
                from configuration.models import ProjectTaskProgress, ProjectWorkflowState
                
                # プロジェクトを検索
                projects_to_delete = Project.objects.filter(
                    models.Q(name=project_name) | models.Q(folder_name=project_name)
                )
                
                if projects_to_delete.exists():
                    for project in projects_to_delete:
                        print(f"削除対象プロジェクト: {project.name} (ID: {project.id})")
                        
                        # 1. Resultレコードを先に削除（PROTECT制約を回避）
                        result_count = Result.objects.filter(project=project).count()
                        if result_count > 0:
                            Result.objects.filter(project=project).delete()
                            print(f"Result レコードを削除: {result_count}件")
                        
                        # 2. Annotationレコードを削除
                        annotation_count = Annotation.objects.filter(image__project=project).count()
                        if annotation_count > 0:
                            Annotation.objects.filter(image__project=project).delete()
                            print(f"Annotation レコードを削除: {annotation_count}件")
                        
                        # 3. ImageFileレコードを削除
                        image_count = ImageFile.objects.filter(project=project).count()
                        if image_count > 0:
                            ImageFile.objects.filter(project=project).delete()
                            print(f"ImageFile レコードを削除: {image_count}件")
                        
                        # 4. Labelレコードを削除
                        label_count = Label.objects.filter(project=project).count()
                        if label_count > 0:
                            Label.objects.filter(project=project).delete()
                            print(f"Label レコードを削除: {label_count}件")
                        
                        # 5. ProjectTaskProgressレコードを削除
                        task_progress_count = ProjectTaskProgress.objects.filter(project=project).count()
                        if task_progress_count > 0:
                            ProjectTaskProgress.objects.filter(project=project).delete()
                            print(f"ProjectTaskProgress レコードを削除: {task_progress_count}件")
                        
                        # 6. ProjectWorkflowStateレコードを削除
                        try:
                            workflow_state = ProjectWorkflowState.objects.filter(project=project)
                            if workflow_state.exists():
                                workflow_state.delete()
                                print(f"ProjectWorkflowState レコードを削除: 1件")
                        except ProjectWorkflowState.DoesNotExist:
                            pass
                        
                        # 7. 最後にプロジェクト自体を削除
                        project.delete()
                        deleted_db_records += 1
                        print(f"プロジェクト削除完了: {project.name}")
                    
                    print(f"データベースから{deleted_db_records}件のプロジェクトを削除: {project_name}")
                else:
                    print(f"データベースに該当するプロジェクトが見つかりません: {project_name}")
                
        except ImportError as import_error:
            print(f"delete_project: annotator.modelsのインポートに失敗: {import_error}")
        except Exception as db_error:
            print(f"delete_project: データベース削除でエラー: {db_error}")
            # データベース削除に失敗した場合は例外を再発生させる
            raise db_error
        
        # データベース削除が成功した場合のみ、物理ディレクトリを削除
        try:
            shutil.rmtree(project_dir)
            print(f"プロジェクトディレクトリを削除: {project_dir}")
        except Exception as file_error:
            print(f"ファイル削除エラー: {file_error}")
            # ファイル削除に失敗してもデータベースは削除済みなので、警告として処理
            return JsonResponse({
                'success': True,
                'message': f'プロジェクト "{project_name}" をデータベースから削除しました（ファイル削除に一部失敗）',
                'warning': f'ファイル削除エラー: {str(file_error)}'
            })
        
        return JsonResponse({
            'success': True,
            'message': f'プロジェクト "{project_name}" を完全に削除しました（DB: {deleted_db_records}件、ファイル: 削除済み）'
        })
        
    except Exception as e:
        print(f"Error in delete_project: {e}")
        return JsonResponse({'success': False, 'error': f'プロジェクト削除中にエラーが発生しました: {str(e)}'})


def get_project_info(request):
    """プロジェクト情報取得API"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'GET method required'})
    
    try:
        project_name = request.GET.get('project_name', '').strip()
        
        if not project_name:
            return JsonResponse({'success': False, 'error': 'プロジェクト名を指定してください'})
        
        project_root = settings.BASE_DIR.parent
        data_collection_dir = project_root / 'data_collection'
        project_dir = data_collection_dir / project_name
        
        if not project_dir.exists():
            return JsonResponse({'success': False, 'error': f'プロジェクト "{project_name}" が見つかりません'})
        
        # プロジェクト情報を取得
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')
        image_count = 0
        total_size = 0
        file_list = []
        
        for file_path in project_dir.rglob('*'):
            if file_path.is_file():
                file_size = file_path.stat().st_size
                total_size += file_size
                
                if file_path.suffix.lower() in image_extensions:
                    image_count += 1
                    file_list.append({
                        'name': file_path.name,
                        'relative_path': str(file_path.relative_to(project_dir)),
                        'size': file_size
                    })
        
        # サイズを適切な単位で表示
        if total_size < 1024:
            size_str = f"{total_size} B"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        elif total_size < 1024 * 1024 * 1024:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{total_size / (1024 * 1024 * 1024):.1f} GB"
        
        return JsonResponse({
            'success': True,
            'project_info': {
                'name': project_name,
                'path': str(project_dir),
                'image_count': image_count,
                'total_size': total_size,
                'size_str': size_str,
                'files': file_list[:100]  # 最初の100ファイルのみ返す
            }
        })
        
    except Exception as e:
        print(f"Error in get_project_info: {e}")
        return JsonResponse({'success': False, 'error': f'予期しないエラーが発生しました: {str(e)}'})


def set_active_project(request):
    """プロジェクトをアクティブ化するAPI"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'})
    try:
        # project_idまたはproject_nameをPOSTデータから取得
        project_id = request.POST.get('project_id')
        project_name = request.POST.get('project_name')
        if not project_id and not project_name:
            # JSON形式の場合
            import json
            try:
                data = json.loads(request.body)
                project_id = data.get('project_id')
                project_name = data.get('project_name')
            except Exception:
                pass
        if not project_id and not project_name:
            return JsonResponse({'success': False, 'error': 'project_idまたはproject_nameが指定されていません'})
        from annotator.models import Project
        # すべてのプロジェクトを非アクティブ化
        Project.objects.filter(is_active=True).update(is_active=False)
        # 指定プロジェクトをアクティブ化（name, folder_name両方で検索）
        if project_id:
            updated = Project.objects.filter(id=project_id).update(is_active=True)
        else:
            updated = Project.objects.filter(name=project_name).update(is_active=True)
            if updated == 0:
                updated = Project.objects.filter(folder_name=project_name).update(is_active=True)
        if updated == 0:
            return JsonResponse({'success': False, 'error': '指定されたプロジェクトが見つかりません'})
        # DBの状態を返す（デバッグ用）
        active_projects = list(Project.objects.filter(is_active=True).values('id', 'name', 'folder_name'))
        return JsonResponse({'success': True, 'message': 'プロジェクトをアクティブ化しました', 'active_projects': active_projects})
    except Exception as e:
        print(f"set_active_project error: {e}")
        return JsonResponse({'success': False, 'error': str(e)})
