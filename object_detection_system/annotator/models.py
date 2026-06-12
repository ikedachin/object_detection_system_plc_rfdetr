from django.db import models
import os
from pathlib import Path
from PIL import Image


class Project(models.Model):
    """プロジェクトモデル - data_collectionのフォルダ名に対応"""
    name = models.CharField(max_length=255, unique=True)
    folder_name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)  # 現在選択中のプロジェクト
    cropped = models.BooleanField(default=False)  # cropped画像生成済みフラグ
    save_path = models.CharField(max_length=512, blank=True, null=True, help_text="画像保存先パス")
    active_yaml_path = models.CharField(default='', max_length=512, help_text="アクティブなYAML設定ファイルのパス")
    active_weight_path = models.CharField(default='', max_length=512, help_text="アクティブな重みファイルのパス")

    def __str__(self):
        return self.name
    
    @property
    def auto_images_path(self):
        """画像フォルダのパスを返す"""
        from django.conf import settings
        return os.path.join(self.save_path, 'data_collection', self.folder_name, 'original')
    
    @property
    def manual_images_path(self):
        """manual画像フォルダのパスを返す"""
        from django.conf import settings
        return os.path.join(self.save_path, 'cropped', self.folder_name, 'cropped')
    
    @classmethod
    def get_active_project(cls):
        """現在アクティブなプロジェクトを取得"""
        return cls.objects.filter(is_active=True).first()
    
    def set_active(self):
        """このプロジェクトをアクティブにする"""
        # 他のプロジェクトを非アクティブにする
        Project.objects.update(is_active=False)
        self.is_active = True
        self.save()
    
    def get_project_path(self):
        """プロジェクトフォルダのパスを取得"""
        from django.conf import settings
        return self.save_path or os.path.join(settings.BASE_DIR.parent, 'projects', self.folder_name)
    
    def get_image_count(self):
        """プロジェクト内の画像数を取得"""
        project_path = self.get_project_path()
        if not os.path.exists(project_path):
            return 0
        
        image_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif')
        count = 0
        
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.lower().endswith(image_exts):
                    count += 1
        
        return count
    
    def get_weight_path(self, config_filename):
        """
        設定ファイル名からウエイトファイルのパスを返す
        例: projects/{folder_name}/models/{config_name}/checkpoint_best_regular.pth
        """
        from django.conf import settings
        # configファイル名（拡張子除去）
        print(f"=== get_weight_path called for config: {config_filename} ===")
        normalized_config = str(config_filename).replace('\\', '/')
        config_name = normalized_config.split('/')[0]
        print(f"=== get_weight_path called for config: {config_name} ===")
        # プロジェクトフォルダのパス
        project_root = Path(settings.PROJECTS_DIR) / self.folder_name
        # ウエイトファイルパス
        model_dir = project_root / 'models' / config_name
        for filename in ('checkpoint_best_regular.pth', 'checkpoint_best_ema.pth', 'checkpoint.pth'):
            weight_path = model_dir / filename
            if weight_path.exists():
                print(f"Weight path: {weight_path}")
                return str(weight_path)
        weight_path = model_dir / 'checkpoint_best_regular.pth'
        print(f"Weight path: {weight_path}")
        return str(weight_path)


class Label(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='labels')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#FF0000')  # Hex color for display
    is_active = models.BooleanField(default=False, help_text='このラベルがプロジェクト内でアクティブかどうか')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'name')

    def __str__(self):
        return f"{self.project.name}: {self.name}"

    @classmethod
    def get_active_labels(cls, project_id=None):
        """アクティブなプロジェクトのラベルを取得"""
        active_project = Project.get_active_project()
        # print(f"=== get_active_labels called for project: {active_project} ===")
        if active_project:
            # print(f"retrun : {cls.objects.filter(project=active_project).annotate(usage_count=models.Count('annotation')).order_by('name')}")
            return cls.objects.filter(project=active_project).annotate(usage_count=models.Count('annotation')).order_by('name')
        return cls.objects.none()


class ImageFile(models.Model):
    filename = models.CharField(max_length=255, unique=True)
    width = models.IntegerField()
    height = models.IntegerField()
    is_annotated = models.BooleanField(default=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.filename
    
    @property
    def file_path(self):
        from django.conf import settings
        
        print(f"=== file_path プロパティ呼び出し: {self.filename} ===")
        
        # プロジェクトが指定されている場合は、そのプロジェクトのフォルダから検索
        if self.project:
            print(f"プロジェクト指定あり: {self.project.name}")
            
            # プロジェクトのルートフォルダパス（新構造）
            project_root_path = os.path.join(settings.BASE_DIR.parent, 'projects', self.project.folder_name)
            
            possible_paths = [
                # 新構造
                os.path.join(project_root_path, 'data_collection', self.filename),
                os.path.join(project_root_path, 'annotated', 'images', self.filename),
                os.path.join(project_root_path, 'cropped', self.filename),
                # サブフォルダも検索
                os.path.join(project_root_path, 'annotated', 'images', 'train', self.filename),
                os.path.join(project_root_path, 'annotated', 'images', 'valid', self.filename),
                # ルート直下
                os.path.join(project_root_path, self.filename),
            ]
            
            for path in possible_paths:
                print(f"パス検索中: {path}")
                if os.path.exists(path):
                    print(f"ファイル発見: {path}")
                    return path
                else:
                    print(f"ファイル存在せず: {path}")
        else:
            print("プロジェクト指定なし")
        
        # 新フォルダ構成での画像検索（デフォルトプロジェクト）
        possible_paths = [
            os.path.join(settings.ANNOTATION_IMAGES_DIR, self.filename),
            os.path.join(settings.DATA_COLLECTION_DIR, self.filename),
            os.path.join(settings.CROP_PREPARATION_CROPPED_DIR, self.filename),
            # 下位互換性
            os.path.join(settings.BASE_IMAGES_DIR, self.filename),
        ]
        
        for path in possible_paths:
            print(f"フォールバック検索中: {path}")
            if os.path.exists(path):
                print(f"フォールバックで発見: {path}")
                return path
        
        # ファイルが見つからない場合はデフォルトパスを返す
        default_path = os.path.join(settings.ANNOTATION_IMAGES_DIR, self.filename)
        print(f"デフォルトパスを返却: {default_path}")
        return default_path
    
    @property
    def image_url(self):
        """画像のURLを返す"""
        from django.urls import reverse
        return reverse('annotator:serve_image', kwargs={'filename': self.filename})
    
    def get_image_dimensions(self):
        try:
            with Image.open(self.file_path) as img:
                return img.size
        except Exception:
            return (0, 0)

    class Meta:
        ordering = ['filename']
        


class Annotation(models.Model):
    image = models.ForeignKey(ImageFile, on_delete=models.CASCADE, related_name='annotations')
    label = models.ForeignKey(Label, on_delete=models.CASCADE)
    x_center = models.FloatField()  # normalized bbox format: center x normalized (0-1)
    y_center = models.FloatField()  # normalized bbox format: center y normalized (0-1)
    width = models.FloatField()     # normalized bbox format: width normalized (0-1)
    height = models.FloatField()    # normalized bbox format: height normalized (0-1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.image.filename} - {self.label.name}"
    
    def to_bbox_label_format(self):
        """Convert to normalized bbox format string"""
        return f"{self.label.id} {self.x_center} {self.y_center} {self.width} {self.height}"


# class YamlConfig(models.Model):
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='yaml_configs')
#     config_name = models.CharField(max_length=255)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ('project', 'config_name')

#     def __str__(self):
#         return f"{self.project.name} - {self.config_name}"


# class Weight(models.Model):
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='weights')
#     weight_path = models.CharField(max_length=255)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ('project', 'weight_path')

#     def __str__(self):
#         return f"{self.project.name} - {self.weight_path}"
