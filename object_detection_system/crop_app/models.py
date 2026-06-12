from django.db import models
from django.contrib.auth.models import User
from annotator.models import Project
import os
from django.conf import settings


class CropSession(models.Model):
    """切り取り作業のセッション管理"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='crop_app_sessions', verbose_name="プロジェクト")
    session_name = models.CharField(max_length=200, verbose_name="セッション名")
    source_folder = models.CharField(
        max_length=20,
        choices=[
            ('auto', '自動収集画像'),
            ('manual', '手動収集画像'),
            ('annotation', 'アノテーション画像'),
            ('base_images', 'ベース画像'),
        ],
        default='auto',
        verbose_name="元画像フォルダ"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    is_completed = models.BooleanField(default=False, verbose_name="完了フラグ")
    notes = models.TextField(blank=True, verbose_name="メモ")
    
    # 統計情報
    total_images = models.IntegerField(default=0, verbose_name="総画像数")
    processed_images = models.IntegerField(default=0, verbose_name="処理済み画像数")
    total_crop_areas = models.IntegerField(default=0, verbose_name="総切り取り領域数")

    class Meta:
        verbose_name = "切り取りセッション"
        verbose_name_plural = "切り取りセッション"
        ordering = ['-created_at']
        unique_together = ['project', 'session_name']

    def __str__(self):
        return f"{self.project.name} - {self.session_name}"
    
    @property
    def progress_percentage(self):
        """進捗率を計算"""
        if self.total_images == 0:
            return 0
        return (self.processed_images / self.total_images) * 100
    
    @property
    def source_path(self):
        """元画像フォルダのパスを取得"""
        if self.source_folder == 'auto':
            return self.project.auto_images_path
        elif self.source_folder == 'manual':
            return self.project.manual_images_path
        elif self.source_folder == 'annotation':
            return os.path.join(settings.ANNOTATION_IMAGES_DIR)
        elif self.source_folder == 'base_images':
            return os.path.join(settings.BASE_IMAGES_DIR)
        return None
    
    @property
    def crop_output_path(self):
        """切り取り出力フォルダのパスを取得"""
        base_path = os.path.join(settings.BASE_DIR.parent, 'crop_preparation', 'cropped', self.project.folder_name)
        session_path = os.path.join(base_path, self.session_name)
        os.makedirs(session_path, exist_ok=True)
        return session_path
    
    def update_statistics(self):
        """統計情報を更新"""
        source_path = self.source_path
        if source_path and os.path.exists(source_path):
            image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')
            self.total_images = len([f for f in os.listdir(source_path) 
                                   if f.lower().endswith(image_extensions)])
        
        self.processed_images = self.crop_images.filter(is_processed=True).count()
        self.total_crop_areas = sum(img.crop_areas.count() for img in self.crop_images.all())
        self.save()


class CropImage(models.Model):
    """切り取り対象の画像"""
    session = models.ForeignKey(CropSession, on_delete=models.CASCADE, related_name='crop_images', verbose_name="セッション")
    image_name = models.CharField(max_length=255, verbose_name="画像ファイル名")
    original_path = models.TextField(verbose_name="元画像パス")
    width = models.IntegerField(default=0, verbose_name="幅")
    height = models.IntegerField(default=0, verbose_name="高さ")
    is_processed = models.BooleanField(default=False, verbose_name="処理済み")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="追加日時")
    notes = models.TextField(blank=True, verbose_name="メモ")

    class Meta:
        verbose_name = "切り取り画像"
        verbose_name_plural = "切り取り画像"
        ordering = ['image_name']
        unique_together = ['session', 'image_name']

    def __str__(self):
        return f"{self.session.session_name} - {self.image_name}"
    
    @property
    def file_path(self):
        """画像ファイルの絶対パスを取得"""
        if os.path.isabs(self.original_path):
            return self.original_path
        return os.path.join(self.session.source_path, self.image_name)
    
    @property
    def crop_count(self):
        """この画像の切り取り領域数"""
        return self.crop_areas.count()


class CropArea(models.Model):
    """切り取り領域の情報"""
    crop_image = models.ForeignKey(CropImage, on_delete=models.CASCADE, related_name='crop_areas', verbose_name="対象画像")
    x = models.IntegerField(verbose_name="X座標")
    y = models.IntegerField(verbose_name="Y座標")
    width = models.IntegerField(verbose_name="幅")
    height = models.IntegerField(verbose_name="高さ")
    label = models.CharField(max_length=100, blank=True, verbose_name="ラベル")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    cropped_image_path = models.CharField(max_length=500, blank=True, verbose_name="切り取り後画像パス")
    confidence = models.FloatField(default=1.0, verbose_name="信頼度")

    class Meta:
        verbose_name = "切り取り領域"
        verbose_name_plural = "切り取り領域"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.crop_image.image_name} - {self.label} ({self.x},{self.y})"
    
    def save_cropped_image(self):
        """切り取った画像を保存"""
        try:
            from PIL import Image
            
            # 元画像を開く
            with Image.open(self.crop_image.file_path) as img:
                # 切り取り領域を指定
                box = (self.x, self.y, self.x + self.width, self.y + self.height)
                cropped = img.crop(box)
                
                # 保存先パスを作成
                output_dir = self.crop_image.session.crop_output_path
                filename = f"{self.crop_image.image_name}_{self.label}_{self.id}.jpg"
                output_path = os.path.join(output_dir, filename)
                
                # 画像を保存
                cropped.save(output_path, 'JPEG', quality=95)
                
                # パスを記録
                self.cropped_image_path = output_path
                self.save()
                
                return output_path
        except Exception as e:
            print(f"切り取り画像の保存でエラー: {e}")
            return None


class CropProgress(models.Model):
    """プロジェクトごとの切り取り進捗管理"""
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='crop_app_progress', verbose_name="プロジェクト")
    total_sessions = models.IntegerField(default=0, verbose_name="総セッション数")
    completed_sessions = models.IntegerField(default=0, verbose_name="完了セッション数")
    total_images = models.IntegerField(default=0, verbose_name="総画像数")
    processed_images = models.IntegerField(default=0, verbose_name="処理済み画像数")
    total_crop_areas = models.IntegerField(default=0, verbose_name="総切り取り領域数")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最終更新日時")

    class Meta:
        verbose_name = "切り取り進捗"
        verbose_name_plural = "切り取り進捗"

    def __str__(self):
        return f"{self.project.name} - 切り取り進捗: {self.progress_percentage():.1f}%"
    
    def progress_percentage(self):
        """進捗率を計算"""
        if self.total_images == 0:
            return 0
        return (self.processed_images / self.total_images) * 100
    
    def update_progress(self):
        """進捗情報を更新"""
        sessions = self.project.crop_app_sessions.all()
        
        self.total_sessions = sessions.count()
        self.completed_sessions = sessions.filter(is_completed=True).count()
        
        # 全セッションの統計を集計
        self.total_images = sum(session.total_images for session in sessions)
        self.processed_images = sum(session.processed_images for session in sessions)
        self.total_crop_areas = sum(session.total_crop_areas for session in sessions)
        
        self.save()


class CropTemplate(models.Model):
    """切り取りテンプレート - よく使用する切り取り設定を保存"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='crop_templates', verbose_name="プロジェクト")
    template_name = models.CharField(max_length=100, verbose_name="テンプレート名")
    label = models.CharField(max_length=100, verbose_name="ラベル")
    width = models.IntegerField(verbose_name="幅")
    height = models.IntegerField(verbose_name="高さ")
    description = models.TextField(blank=True, verbose_name="説明")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    is_active = models.BooleanField(default=True, verbose_name="アクティブ")

    class Meta:
        verbose_name = "切り取りテンプレート"
        verbose_name_plural = "切り取りテンプレート"
        ordering = ['template_name']
        unique_together = ['project', 'template_name']

    def __str__(self):
        return f"{self.project.name} - {self.template_name} ({self.width}x{self.height})"
