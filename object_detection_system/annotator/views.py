from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.contrib import messages
from django.urls import reverse
import os
import json
import shutil
import random
import mimetypes
from datetime import datetime
from .models import ImageFile, Label, Annotation, Project


def _empty_coco_dataset(labels):
    categories = [
        {
            'id': index,
            'name': label.name,
            'supercategory': 'object',
        }
        for index, label in enumerate(labels)
    ]
    return {
        'images': [],
        'annotations': [],
        'categories': categories,
    }


def index(request):
    """画像一覧ページ"""
    # 現在のプロジェクトを取得
    current_project = Project.get_active_project()
    print("Current project:", current_project)
    # プロジェクトが全く存在しない場合
    if Project.objects.count() == 0:
        messages.warning(request, 'プロジェクトがありません。新規作成してください。')
        return redirect(reverse('configuration:project_manager'))
    # アクティブなプロジェクトがない場合
    if not current_project:
        messages.warning(request, 'アクティブなプロジェクトがありません。プロジェクトを選択してください。')
        return redirect(reverse('configuration:project_manager'))
    # プロジェクトが選択されている場合はそのプロジェクトの画像のみ表示
    if current_project:
        images = ImageFile.objects.filter(project=current_project).order_by('filename', 'id')
        labels = Label.objects.filter(project=current_project).annotate(usage_count=Count('annotation')).order_by('name')
    else:
        images = ImageFile.objects.all().order_by('filename', 'id')
        labels = Label.objects.all().annotate(usage_count=Count('annotation')).order_by('name')
    # ラベルの使用回数を取得
    # labels = Label.objects.annotate(usage_count=Count('annotation')).order_by('name')
    
    # アノテーション済み画像数を計算
    annotated_count = images.filter(is_annotated=True).count()
    
    # 利用可能なプロジェクトを取得
    projects = Project.objects.all().order_by('name')
    
    # print(current_project.cropped)

    # Projectテーブルのcroppedフラグで判定
    use_cropped = "data_collection"  # デフォルトは元画像
    if current_project.cropped:
        use_cropped = "cropped"
    print(f"Use cropped images: {use_cropped}")

    return render(request, 'annotator/index.html', {
        'images': images,
        'labels': labels,
        'annotated_count': annotated_count,
        'projects': projects,
        'current_project': current_project,
        'cropped': use_cropped,
        # 'project_dir': settings.BASE_DIR.parent / 'projects' / current_project.folder_name
    })


def annotate(request, image_id: int, cropped: str = "data_collection"):
    """アノテーション画面"""
    print(f"=== アノテーション画面: image_id={image_id}, cropped={cropped} ===")
    # 現在のプロジェクトを取得
    current_project = Project.get_active_project()
    print("Current project:", current_project, current_project.cropped)
    image = get_object_or_404(ImageFile, id=image_id)
    print(f"Selected image: {image.filename}, Project: {image.project.name if image.project else 'None'}")
    
    for k, v in current_project.__dict__.items():
        print(f"[DEBUG]{annotate.__name__} プロジェクト情報：{k}: {v}")

    for k, v in image.__dict__.items():
        print(f"[DEBUG]{annotate.__name__} 画像情報：{k}: {v}")


    # プロジェクトが選択されていない場合はプロジェクト選択画面にリダイレクト
    if not current_project:
        messages.warning(request, 'プロジェクトを選択してください。')
        return redirect('annotator:project_list')

    # 画像が現在のプロジェクトに属していない場合もプロジェクト選択画面にリダイレクト
    if image.project != current_project:
        messages.warning(request, f'この画像は現在選択中のプロジェクト "{current_project.name}" に属していません。')
        return redirect('annotator:project_list')

    labels = Label.objects.filter(project=current_project).annotate(usage_count=Count('annotation')).order_by('name')
    annotations = Annotation.objects.filter(image=image)

    # --- cropped画像を使うかどうか判定 ---
    # use_cropped = False
    # # GETパラメータまたはセッションで判定（必要に応じて変更）
    # if request.GET.get('use_cropped') == 'true' or request.session.get('use_cropped'):
    #     use_cropped = True
    project_root_path = settings.PROJECTS_DIR / current_project.folder_name
    # project_root_path = os.path.join(settings.BASE_DIR.parent, 'projects', current_project.folder_name)
    print(f'project_dir: {settings.PROJECTS_DIR}')
    print(f"Project root path: {project_root_path}")
    # 画像パスを決定
    image_url = None
    if current_project.cropped:
        image_url = project_root_path / 'cropped' / image.filename
        print(f"Using cropped image URL: {image_url}")
    else:
        image_url = project_root_path / 'data_collection' / image.filename

    if image_url.exists():
        print("image is exist: ", image_url)
    else:
        print("image is not exist: ", image_url)
        # 画像が存在しない場合は404エラーを返す
        raise Http404("画像が見つかりません")

    # 次の画像と前の画像を取得（同じプロジェクト内で、一覧と同じ filename 順に合わせる）
    ordered = ImageFile.objects.filter(project=current_project).order_by('filename', 'id')
    next_image = ordered.filter(
        Q(filename__gt=image.filename) |
        (Q(filename=image.filename) & Q(id__gt=image.id))
    ).first()
    prev_image = ordered.filter(
        Q(filename__lt=image.filename) |
        (Q(filename=image.filename) & Q(id__lt=image.id))
    ).order_by('-filename', '-id').first()
    
    image_url = reverse('annotator:serve_image', kwargs={'filename': image.filename})

    return render(request, 'annotator/annotate.html', {
        'image': image,
        'labels': labels,
        'annotations': annotations,
        'next_image': next_image,
        'prev_image': prev_image,
        'current_project': current_project,
        'image_url': image_url,
        'cropped': cropped
    })


@csrf_exempt
@require_http_methods(["POST"]) # POSTリクエストのみを許可
def save_annotations(request, image_id):
    """アノテーションデータを保存"""
    image = get_object_or_404(ImageFile, id=image_id)
    
    try:
        data = json.loads(request.body)
        annotations_data = data.get('annotations', [])
        
        # 既存のアノテーションを削除
        Annotation.objects.filter(image=image).delete()
        
        # 新しいアノテーションを保存
        for ann_data in annotations_data:
            label = get_object_or_404(Label, id=ann_data['label_id'])
            Annotation.objects.create(
                image=image,
                label=label,
                x_center=ann_data['x_center'],
                y_center=ann_data['y_center'],
                width=ann_data['width'],
                height=ann_data['height']
            )
        
        # 画像をアノテーション済みにマーク
        if annotations_data:
            image.is_annotated = True
        else:
            image.is_annotated = False

        image.save()
        
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ラベルをアクティブにするAPI
@csrf_exempt
@require_http_methods(["POST"])
def set_active_label(request):
    """指定したラベルをアクティブにする（同じプロジェクト内で1つだけ）"""
    import json
    from .models import Label
    try:
        data = json.loads(request.body)
        label_id = data.get('label_id')
        if not label_id:
            return JsonResponse({'status': 'error', 'message': 'label_idが必要です'})
        label = get_object_or_404(Label, id=label_id)
        # 同じプロジェクト内の他のラベルを非アクティブ化
        Label.objects.filter(project=label.project).update(is_active=False)
        # このラベルをアクティブ化
        label.is_active = True
        label.save()
        return JsonResponse({'status': 'success', 'active_label_id': label.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    

def load_images(request):
    """base_imagesフォルダから画像を読み込み"""
    try:
        base_images_dir = settings.BASE_IMAGES_DIR
        if not os.path.exists(base_images_dir):
            os.makedirs(base_images_dir)
            return JsonResponse({'status': 'error', 'message': 'base_imagesフォルダが見つかりません'})
        
        # 画像ファイルを検索
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        image_files = [f for f in os.listdir(base_images_dir) 
                      if f.lower().endswith(image_extensions)]
        image_files = [f for f in image_files if ("data_collection" in f.lower()) or ("cropped" in f.lower())]  # modelsフォルダ内の画像のみ対象
        
        created_count = 0
        for filename in image_files:
            if not ImageFile.objects.filter(filename=filename).exists():
                filepath = os.path.join(base_images_dir, filename)
                try:
                    from PIL import Image
                    with Image.open(filepath) as img:
                        width, height = img.size
                    
                    ImageFile.objects.create(
                        filename=filename,
                        width=width,
                        height=height
                    )
                    created_count += 1
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
        
        return JsonResponse({
            'status': 'success', 
            'message': f'{created_count}個の新しい画像を読み込みました'
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def split_dataset(request):
    """データセットをtrain/validに分割し、学習用YAMLファイルを生成"""
    try:
        data = json.loads(request.body)
        split_ratio = float(data.get('split_ratio', 0.8))  # デフォルト8:2
        target_size = int(data.get('image_size', 640))  # デフォルト640x640
        
        print(f"[DEBUG {split_dataset.__name__}] data: {data}")
        # アノテーション済みの画像のみを対象
        annotated_images = ImageFile.objects.filter(
                            is_annotated=True, 
                            project__name=data['projectname']
                            )

        # print(f"[DEBUG {split_dataset.__name__}] アノテーション済み画像数: {annotated_images.count()}")

        # labelの取得
        labels = Label.get_active_labels()
        
        if not labels.exists():
            return JsonResponse({'status': 'error', 'message': 'ラベルが存在しません'})
        print(f"[DEBUG {split_dataset.__name__}] ラベル数: {labels.count()}")

        label2id = {label.name: i for i, label in enumerate(labels)}
        # id2label = {i: label.name for i, label in enumerate(labels)}
        # print(f"[DEBUG {split_dataset.__name__}] ラベルIDマッピング: {label2id}")
        # print(f"[DEBUG {split_dataset.__name__}] IDからラベル名のマッピング: {id2label}")

        if not annotated_images.exists():
            return JsonResponse({'status': 'error', 'message': 'アノテーション済みの画像がありません'})
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if data['cropped'] == "cropped":
            sub_dir = "cropped"
        else:
            sub_dir = "data_collection"
        
        # 日付付きの出力フォルダを作成
        dated_output_dir = settings.PROJECTS_DIR / data['projectname'] / 'annotated' / sub_dir
        print(f"[DEBUG {split_dataset.__name__}] 出力フォルダ: {dated_output_dir}")

        # 画像とラベルの保存先ディレクトリを作成
        train_images_dir = dated_output_dir / 'images' / 'train'
        valid_images_dir = dated_output_dir / 'images' / 'valid'
        train_labels_dir = dated_output_dir / 'labels' / 'train'
        valid_labels_dir = dated_output_dir / 'labels' / 'valid'
        annotations_dir = dated_output_dir / 'annotations'
        
        # ランダムに分割
        images_list = list(annotated_images)
        random.shuffle(images_list)
        
        train_count = int(len(images_list) * split_ratio)
        train_images = images_list[:train_count]
        valid_images = images_list[train_count:]
        print(f"[DEBUG {split_dataset.__name__}] 分割結果: train={len(train_images)}, valid={len(valid_images)}")
        
        # 画像処理に必要なライブラリをインポート
        from PIL import Image, ImageOps
        
        
        label_list = list(labels)
        names_yaml_list = []
        coco_by_split = {
            'train': _empty_coco_dataset(label_list),
            'valid': _empty_coco_dataset(label_list),
        }
        coco_annotation_id = 1
        # ファイルをコピー・リサイズ
        for split_name, images, target_img_dir, target_label_dir in [
            ('train', train_images, train_images_dir, train_labels_dir),
            ('valid', valid_images, valid_images_dir, valid_labels_dir),
        ]:
            os.makedirs(target_img_dir, exist_ok=True)
            os.makedirs(target_label_dir, exist_ok=True)

            for i, image in enumerate(images):
                # 画像ファイルを読み込み
                # print(f"[DEBUG {split_dataset.__name__}] 処理中の画像: {data['projectname']}, インデックス: {i+1}/{len(images)}")
                src_img_path = settings.PROJECTS_DIR / data['projectname'] / sub_dir / image.filename
                dst_img_path = os.path.join(target_img_dir, image.filename)

                # print(f"[DEBUG {split_dataset.__name__}] 処理中の画像: {src_img_path}, インデックス: {i+1}/{len(images)}")
                # print(f"[DEBUG {split_dataset.__name__}] 処理中の画像: {image.filename}, 保存先: {dst_img_path}")
                # print(os.path.exists(src_img_path), os.path.exists(dst_img_path))
                
                # 画像をリサイズ・パディング
                with Image.open(src_img_path) as img:
                    # RGBに変換（必要に応じて）
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    original_width, original_height = img.size
                    
                    # 画像をターゲットサイズに合わせてリサイズ（アスペクト比を保持）
                    img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
                    resized_width, resized_height = img.size
                    
                    # 正方形のキャンバスを作成（白でパディング）
                    new_img = Image.new('RGB', (target_size, target_size), (255, 255, 255))
                    
                    # 画像をキャンバスの左上に配置
                    paste_x = 0
                    paste_y = 0
                    new_img.paste(img, (paste_x, paste_y))
                    
                    # リサイズした画像を保存
                    new_img.save(dst_img_path, quality=95)
                    
                    # スケール比とオフセットを計算
                    scale_x = resized_width / original_width
                    scale_y = resized_height / original_height
                    offset_x = paste_x / target_size
                    offset_y = paste_y / target_size
                
                # ラベルファイルを作成（座標を変換）
                label_filename = os.path.splitext(image.filename)[0] + '.txt'
                label_path = os.path.join(target_label_dir, label_filename)
                # print(f"[DEBUG {split_dataset.__name__}] ラベルファイル: {label_path}")

                
                coco_image_id = len(coco_by_split[split_name]['images']) + 1
                coco_by_split[split_name]['images'].append({
                    'id': coco_image_id,
                    'file_name': image.filename,
                    'width': target_size,
                    'height': target_size,
                })

                with open(label_path, 'w') as f:
                    annotations = Annotation.objects.filter(image=image)
                    for ann in annotations:
                        # print(f"[DEBUG {split_dataset.__name__}] アノテーション: {ann.label.name}")
                        # print(f"[DEBUG {split_dataset.__name__}] アノテーション: {ann.label.name}, x_center={ann.x_center}, y_center={ann.y_center}, width={ann.width}, height={ann.height}")
                        # 元の座標を取得
                        orig_x_center = ann.x_center
                        orig_y_center = ann.y_center
                        orig_width = ann.width
                        orig_height = ann.height
                        
                        # 元の画像サイズでの絶対座標に変換
                        abs_x_center = orig_x_center * original_width
                        abs_y_center = orig_y_center * original_height
                        abs_width = orig_width * original_width
                        abs_height = orig_height * original_height
                        
                        # リサイズ後の絶対座標に変換
                        new_abs_x_center = abs_x_center * scale_x + paste_x
                        new_abs_y_center = abs_y_center * scale_y + paste_y
                        new_abs_width = abs_width * scale_x
                        new_abs_height = abs_height * scale_y
                        
                        # 新しい画像サイズでの相対座標に変換
                        new_x_center = new_abs_x_center / target_size
                        new_y_center = new_abs_y_center / target_size
                        new_width = new_abs_width / target_size
                        new_height = new_abs_height / target_size
                        
                        # 座標が範囲内に収まるようにクリップ
                        new_x_center = max(0, min(1, new_x_center))
                        new_y_center = max(0, min(1, new_y_center))
                        new_width = max(0, min(1, new_width))
                        new_height = max(0, min(1, new_height))
                        # print(f"[DEBUG {split_dataset.__name__}] 書き込み: {ann.label.name} {label2id[ann.label.name]}")
                        if [label2id[ann.label.name], ann.label.name] not in names_yaml_list:
                            names_yaml_list.append([label2id[ann.label.name], ann.label.name])
                        f.write(f"{label2id[ann.label.name]} {new_x_center:.6f} {new_y_center:.6f} {new_width:.6f} {new_height:.6f}\n")

                        coco_x = max(0.0, new_abs_x_center - new_abs_width / 2)
                        coco_y = max(0.0, new_abs_y_center - new_abs_height / 2)
                        coco_w = max(0.0, min(float(target_size) - coco_x, new_abs_width))
                        coco_h = max(0.0, min(float(target_size) - coco_y, new_abs_height))
                        if coco_w > 0 and coco_h > 0:
                            coco_by_split[split_name]['annotations'].append({
                                'id': coco_annotation_id,
                                'image_id': coco_image_id,
                                'category_id': label2id[ann.label.name],
                                'bbox': [
                                    round(coco_x, 6),
                                    round(coco_y, 6),
                                    round(coco_w, 6),
                                    round(coco_h, 6),
                                ],
                                'area': round(coco_w * coco_h, 6),
                                'iscrowd': 0,
                            })
                            coco_annotation_id += 1
        # YAMLファイルを生成
        os.makedirs(dated_output_dir, exist_ok=True)
        
        # ファイル名をプロジェクト名_data_collection or cropped の形式で保存
        yaml_filename = f"{data['projectname']}_{sub_dir}.yaml"
        yaml_path = os.path.join(dated_output_dir, yaml_filename)
        
        # ラベルの情報を取得
        # all_labels = Label.objects.all().order_by('id')
        # label_names = {label.id: label.name for label in all_labels}
        
        
        # YAMLファイルの内容を作成
        print(f"[DEBUG {split_dataset.__name__}] ラベルの情報: {names_yaml_list}")
        unique_names_list = list(set(tuple(name) for name in names_yaml_list))
        sorted_names = sorted(unique_names_list, key=lambda x: x[0])  # IDでソート
        names_yaml = "\n".join([f"  {idx}: {name}" for idx, name in sorted_names])

        yaml_content = f"""# Train/val/test sets as 1) dir: path/to/imgs, 2) file: path/to/imgs.txt, or 3) list: [path/to/imgs1, path/to/imgs2, ..]
path: {dated_output_dir} # dataset root dir
train: images/train # train images
val: images/valid # val images
test: # test images (optional)

# Classes
names:
{names_yaml}
"""
        

        # クラス名の部分を追加
        # クラスIDは0始まりの互換BBoxラベルとして保存する
        print(f"[DEBUG {split_dataset.__name__}] YAMLファイル内容:\n{yaml_content}")

        # YAMLファイルを保存
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)

        os.makedirs(annotations_dir, exist_ok=True)
        for split_name, coco_data in coco_by_split.items():
            coco_path = annotations_dir / f'instances_{split_name}.json'
            with open(coco_path, 'w', encoding='utf-8') as f:
                json.dump(coco_data, f, ensure_ascii=False, indent=2)
        
        return JsonResponse({
            'status': 'success',
            'message': f'データセットを分割しました (train: {len(train_images)}, valid: {len(valid_images)})\n画像サイズ: {target_size}x{target_size}\n出力フォルダ: output_{timestamp}\nYAMLファイルを生成しました: {yaml_filename}'
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def add_label(request):
    """ラベルを追加"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        color = data.get('color', '#FF0000')

        # プロジェクト取得
        current_project = Project.get_active_project()
        if not current_project:
            return JsonResponse({'status': 'error', 'message': 'プロジェクトが選択されていません'})

        if not name:
            return JsonResponse({'status': 'error', 'message': 'ラベル名が必要です'})

        if Label.objects.filter(project=current_project, name=name).exists():
            return JsonResponse({'status': 'error', 'message': 'このラベル名は既に存在します'})

        label = Label.objects.create(project=current_project, name=name, color=color)

        return JsonResponse({
            'status': 'success',
            'label': {
                'id': label.id,
                'name': label.name,
                'color': label.color
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSONデータの形式が正しくありません'})
    except Exception as e:
        # データベースの整合性制約エラーの場合
        if 'UNIQUE constraint failed' in str(e):
            return JsonResponse({'status': 'error', 'message': 'このラベル名は既に使用されています'})
        return JsonResponse({'status': 'error', 'message': f'ラベルの作成に失敗しました: {str(e)}'})


@csrf_exempt
@require_http_methods(["POST"])
def delete_label(request, label_id):
    """ラベルを削除"""
    try:
        label = get_object_or_404(Label, id=label_id)
        
        # このラベルを使用しているアノテーションがあるかチェック
        annotation_count = Annotation.objects.filter(label=label).count()
        if annotation_count > 0:
            return JsonResponse({
                'status': 'error', 
                'message': f'このラベルは{annotation_count}個のアノテーションで使用されているため削除できません'
            })
        
        label_name = label.name
        label.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'ラベル「{label_name}」を削除しました'
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
@require_http_methods(["POST", "PUT"]) # ラベルの更新はPOST,PUTリクエストのみ
def update_label(request, label_id):
    """ラベルを更新"""
    try:
        label = get_object_or_404(Label, id=label_id)
        data = json.loads(request.body)
        
        name = data.get('name', '').strip()
        color = data.get('color', label.color)
        
        print(f"ラベル更新要求: ID={label_id}, 現在の名前='{label.name}', 新しい名前='{name}'")
        
        if not name:
            return JsonResponse({'status': 'error', 'message': 'ラベル名が必要です'})
        
        # 名前が変更されている場合のみ重複チェック
        if name != label.name:
            existing_label = Label.objects.filter(name=name).first()
            if existing_label:
                print(f"重複チェック: ラベル名 '{name}' は既に存在します (ID: {existing_label.id})")
                return JsonResponse({'status': 'error', 'message': 'このラベル名は既に存在します'})
        
        # ラベル情報を更新（使用中でも編集可能）
        label.name = name
        label.color = color
        label.save()
        
        return JsonResponse({
            'status': 'success',
            'label': {
                'id': label.id,
                'name': label.name,
                'color': label.color
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSONデータの形式が正しくありません'})
    except Exception as e:
        # データベースの整合性制約エラーの場合
        if 'UNIQUE constraint failed' in str(e):
            return JsonResponse({'status': 'error', 'message': 'このラベル名は既に使用されています'})
        return JsonResponse({'status': 'error', 'message': f'ラベルの更新に失敗しました: {str(e)}'})


def serve_image(request, filename):
    """プロジェクトの画像フォルダから画像を配信"""
    print(f"=== 画像リクエスト受信: {filename} ===")
    
    try:
        # まずデータベースから画像を検索
        image_file = ImageFile.objects.filter(filename=filename).first()
        
        if image_file:
            # ImageFileモデルのfile_pathプロパティを使用（プロジェクト対応）
            file_path = image_file.file_path
            print(f"DB経由でのファイルパス: {file_path}")
        else:
            # 従来のfallback（BASE_IMAGES_DIR）
            file_path = os.path.join(settings.BASE_IMAGES_DIR, filename)
            print(f"フォールバックファイルパス: {file_path}")
        
        print(f"最終ファイルパス: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"ファイルが見つかりません: {file_path}")
            
            # プロジェクトが選択されている場合、詳細な探索を行う（新構造）
            current_project = Project.get_active_project()
            if current_project:
                print(f"現在のプロジェクト: {current_project.name}")
                
                # プロジェクトフォルダのルートパス（新構造）
                project_root_path = os.path.join(settings.BASE_DIR.parent, 'projects', current_project.folder_name)
                
                # 新構造での検索パス
                search_paths = [
                    os.path.join(project_root_path, 'data_collection'),
                    os.path.join(project_root_path, 'annotated', 'images'),
                    os.path.join(project_root_path, 'annotated', 'images', 'train'),
                    os.path.join(project_root_path, 'annotated', 'images', 'valid'),
                    os.path.join(project_root_path, 'cropped'),
                    project_root_path,  # ルート直下も検索
                ]
                
                for search_dir in search_paths:
                    candidate_path = os.path.join(search_dir, filename)
                    print(f"検索中: {candidate_path}")
                    if os.path.exists(candidate_path):
                        file_path = candidate_path
                        print(f"見つかりました: {file_path}")
                        break
                else:
                    print(f"すべての検索パスで見つかりませんでした")
                    raise Http404("画像が見つかりません")
            else:
                raise Http404("画像が見つかりません")
        
        print(f"ファイル存在確認: OK")
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        print(f"画像配信成功: {filename}, サイズ: {len(content)}, content-type: {content_type}")
        response = HttpResponse(content, content_type=content_type)
        return response
    except Exception as e:
        print(f"画像配信エラー: {e}")
        raise Http404("画像の配信に失敗しました")


def project(request):
    """プロジェクト一覧ページ"""
    projects = Project.objects.all().order_by('name')
    current_project = Project.get_active_project()
    
    return render(request, 'annotator/project.html', {
        'projects': projects,
        'current_project': current_project
    })




@csrf_exempt
def scan_projects(request):
    """data_collectionフォルダをスキャンしてプロジェクトを自動作成"""
    if request.method == 'POST':
        try:
            data_collection_dir = os.path.join(settings.BASE_DIR.parent, 'data_collection')
            created_count = 0
            
            if not os.path.exists(data_collection_dir):
                return JsonResponse({'success': False, 'error': 'data_collectionフォルダが見つかりません'})
            
            # data_collectionフォルダ内のディレクトリをスキャン
            for item in os.listdir(data_collection_dir):
                item_path = os.path.join(data_collection_dir, item)
                if os.path.isdir(item_path):
                    # プロジェクトが存在しない場合は作成
                    project, created = Project.objects.get_or_create(
                        folder_name=item,
                        defaults={'name': item}
                    )
                    if created:
                        created_count += 1
            
            return JsonResponse({
                'success': True, 
                'message': f'{created_count}個の新しいプロジェクトを作成しました',
                'created_count': created_count
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})



@csrf_exempt
def set_active_project(request, project_id):
    """プロジェクトをアクティブにする（cropped画像有無も返す）"""
    if request.method == 'POST':
        try:
            project = get_object_or_404(Project, id=project_id)
            project.set_active()
            # croppedフォルダの有無と画像数を返す
            import os
            project_root_path = os.path.join(settings.BASE_DIR.parent, 'projects', project.folder_name)
            cropped_path = os.path.join(project_root_path, 'cropped')
            has_cropped = False
            cropped_count = 0
            if os.path.exists(cropped_path) and os.path.isdir(cropped_path):
                cropped_files = [f for f in os.listdir(cropped_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
                if cropped_files:
                    has_cropped = True
                    cropped_count = len(cropped_files)
            return JsonResponse({
                'success': True,
                'message': f'プロジェクト "{project.name}" を選択しました',
                'has_cropped': has_cropped,
                'cropped_count': cropped_count
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})


@csrf_exempt
def load_project_images(request, project_id):
    """指定プロジェクトの画像を読み込む（cropped/original選択対応）"""
    if request.method == 'POST':
        try:
            project = get_object_or_404(Project, id=project_id)
            loaded_count = 0
            # どの画像種別を使うか（"cropped" or "original"）
            use_cropped = False
            if request.body:
                try:
                    body = json.loads(request.body)
                    print(f"リクエストボディ{load_project_images.__name__}: {body}")
                    use_cropped = body.get('use_cropped', False)
                except Exception:
                    pass
            print(f"=== プロジェクト画像読み込み開始: {project.name} ===")
            print(f"プロジェクトフォルダ名: {project.folder_name}")
            project_root_path = os.path.join(settings.BASE_DIR.parent, 'projects', project.folder_name)
            print(f"プロジェクトルートパス: {project_root_path}")
            if not os.path.exists(project_root_path):
                print(f"プロジェクトフォルダが存在しません: {project_root_path}")
                return JsonResponse({'success': False, 'error': f'プロジェクトフォルダが見つかりません: {project.folder_name}'})
            scan_folders = []
            data_collection_path = os.path.join(project_root_path, 'data_collection')
            cropped_path = os.path.join(project_root_path, 'cropped')
            # cropped優先の場合
            if use_cropped and os.path.exists(cropped_path):
                scan_folders.append(('cropped', cropped_path))
                selected = 'cropped'
            else:
                if os.path.exists(data_collection_path):
                    scan_folders.append(('data_collection', data_collection_path))
                selected = 'data_collection'
            # fallback: annotated, train, valid, root直下
            annotated_images_path = os.path.join(project_root_path, 'annotated', 'images')
            if os.path.exists(annotated_images_path):
                scan_folders.append(('annotated_images', annotated_images_path))
                train_path = os.path.join(annotated_images_path, 'train')
                valid_path = os.path.join(annotated_images_path, 'valid')
                if os.path.exists(train_path):
                    scan_folders.append(('annotated_train', train_path))
                if os.path.exists(valid_path):
                    scan_folders.append(('annotated_valid', valid_path))
            if not scan_folders:
                scan_folders.append(('root', project_root_path))
                print("新構造フォルダが見つからないため、ルート直下をスキャンします")
            # 各フォルダをスキャン
            for folder_type, folder_path in scan_folders:
                # print(f"{folder_type}フォルダをチェック: {folder_path}")
                if os.path.exists(folder_path):
                    print(f"{folder_type}フォルダが存在します")
                    files_in_folder = os.listdir(folder_path)
                    # print(f"{folder_type}フォルダ内のファイル数: {len(files_in_folder)}")
                    for filename in files_in_folder:
                        file_path = os.path.join(folder_path, filename)
                        if os.path.isfile(file_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                            # print(f"画像ファイル発見: {filename}")
                            # 画像ファイルが既に存在するかチェック
                            if not ImageFile.objects.filter(filename=filename, project=project).exists():
                                try:
                                    # 画像の寸法を取得
                                    from PIL import Image
                                    with Image.open(file_path) as img:
                                        width, height = img.size
                                    # ImageFileオブジェクトを作成
                                    ImageFile.objects.create(
                                        filename=filename,
                                        width=width,
                                        height=height,
                                        project=project
                                    )
                                    loaded_count += 1
                                    print(f"画像をDBに登録: {filename} ({width}x{height})")
                                except Exception as e:
                                    print(f"画像の処理に失敗: {filename}, エラー: {e}")
                            else:
                                print(f"画像は既にDBに存在: {filename}")
                else:
                    print(f"{folder_type}フォルダが存在しません: {folder_path}")
            print(f"=== 画像読み込み完了: {loaded_count}個の新しい画像 ===")
            print(f"選択された画像種別: {selected}")
            return JsonResponse({
                'success': True,
                'message': f'プロジェクト \"{project.name}\" から {loaded_count}個の画像を読み込みました',
                'loaded_count': loaded_count,
                'cropped_or_not': selected
            })
        except Exception as e:
            print(f"load_project_images エラー: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'POSTリクエストが必要です'})


def get_thumbnail(request, image_id, cropped: str = "original"):
    """サムネイル画像を取得"""
    image = get_object_or_404(ImageFile, id=image_id)
    
    # サムネイルのパスを生成
    thumbnail_path = os.path.join(settings.BASE_DIR.parent, 
                                  'projects', 
                                  image.project.name, 
                                  'thumbnail', 
                                  'data_collection', 
                                  image.filename
                                  )

    if cropped == "cropped":
        # cropped画像のサムネイルパスを生成
        thumbnail_path = os.path.join(settings.BASE_DIR.parent, 
                                  'projects', 
                                  image.project.name, 
                                  'thumbnail', 
                                  'cropped', 
                                  image.filename
                                  )
    
    # print(f"サムネイルパス: {thumbnail_path}, project: {image.project.name if image.project else 'None'}")
    # サムネイルのディレクトリが存在しない場合は作成
    if not os.path.exists(os.path.dirname(thumbnail_path)):
        os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)

    if not os.path.exists(thumbnail_path):
        # サムネイルが存在しない場合は生成
        from PIL import Image as PILImage
        try:
            with PILImage.open(image.file_path) as img:
                img.thumbnail((150, 150), PILImage.Resampling.LANCZOS)
                img.save(thumbnail_path, "JPEG")
        except Exception as e:
            raise Http404(f"サムネイルの生成に失敗しました: {e}")
    
    with open(thumbnail_path, 'rb') as f:
        content = f.read()
        
    return HttpResponse(content, content_type='image/jpeg')

