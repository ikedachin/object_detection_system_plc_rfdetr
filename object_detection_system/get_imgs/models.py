from django.db import models
import os
from django.conf import settings

# Create your models here.

class DataCollectionProject(models.Model):
    """データ収集プロジェクト管理"""
    name = models.CharField(max_length=255, unique=True, verbose_name="プロジェクト名")
    folder_name = models.CharField(max_length=255, unique=True, verbose_name="フォルダ名")
    description = models.TextField(blank=True, verbose_name="説明")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    is_active = models.BooleanField(default=False, verbose_name="アクティブ")
    
    # データ収集関連の統計
    auto_image_count = models.IntegerField(default=0, verbose_name="自動取得画像数")
    manual_image_count = models.IntegerField(default=0, verbose_name="手動取得画像数")
    
    class Meta:
        verbose_name = "データ収集プロジェクト"
        verbose_name_plural = "データ収集プロジェクト"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def images_path(self):
        """画像フォルダのパスを返す（統合されたdata_collectionフォルダ）"""
        return os.path.join(settings.BASE_DIR.parent, 'projects', self.folder_name, 'data_collection')
    
    @property
    def auto_images_path(self):
        """auto画像フォルダのパスを返す（後方互換性のため、images_pathと同じ）"""
        return self.images_path
    
    @property
    def manual_images_path(self):
        """manual画像フォルダのパスを返す（後方互換性のため、images_pathと同じ）"""
        return self.images_path
    
    @property
    def total_image_count(self):
        """総画像数を返す"""
        return self.auto_image_count + self.manual_image_count
    
    @classmethod
    def get_active_project(cls):
        """現在アクティブなプロジェクトを取得"""
        return cls.objects.filter(is_active=True).first()
    
    def set_active(self):
        """このプロジェクトをアクティブにする"""
        # 他のプロジェクトを非アクティブにする
        DataCollectionProject.objects.update(is_active=False)
        self.is_active = True
        self.save()
    
    def update_image_counts(self):
        """画像数を更新"""
        data_collection_path = self.images_path  # 統合されたフォルダを使用
        
        # data_collection フォルダの画像数
        if os.path.exists(data_collection_path):
            total_count = len([f for f in os.listdir(data_collection_path) 
                             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))])
            # 便宜上、auto_image_countに総数を設定
            self.auto_image_count = total_count
            self.manual_image_count = 0
        else:
            self.auto_image_count = 0
            self.manual_image_count = 0
            
        self.save()
    
    def create_folder_structure(self):
        """プロジェクトのフォルダ構造を作成"""
        base_dir = os.path.join(settings.BASE_DIR.parent, 'projects', self.folder_name)
        data_collection_dir = os.path.join(base_dir, 'data_collection')
        annotated_dir = os.path.join(base_dir, 'annotated')
        cropped_dir = os.path.join(base_dir, 'cropped')
        
        # サブフォルダも作成
        # annotated_images_dir = os.path.join(annotated_dir, 'images')
        # annotated_labels_dir = os.path.join(annotated_dir, 'labels')
        # train_images_dir = os.path.join(annotated_images_dir, 'train')
        # valid_images_dir = os.path.join(annotated_images_dir, 'valid')
        # train_labels_dir = os.path.join(annotated_labels_dir, 'train')
        # valid_labels_dir = os.path.join(annotated_labels_dir, 'valid')
        
        # フォルダを作成
        os.makedirs(data_collection_dir, exist_ok=True)
        os.makedirs(cropped_dir, exist_ok=True)
        os.makedirs(annotated_dir, exist_ok=True)
        # os.makedirs(train_images_dir, exist_ok=True)
        # os.makedirs(valid_images_dir, exist_ok=True)
        # os.makedirs(train_labels_dir, exist_ok=True)
        # os.makedirs(valid_labels_dir, exist_ok=True)
        
        return {
            'base_dir': base_dir,
            'data_collection_dir': data_collection_dir,
            'annotated_dir': annotated_dir,
            'cropped_dir': cropped_dir,
            'imgs_dir': data_collection_dir  # 統合された画像フォルダ
        }


class DataCollectionSession(models.Model):
    """データ収集セッション"""
    project = models.ForeignKey(DataCollectionProject, on_delete=models.CASCADE, related_name='sessions', verbose_name="プロジェクト")
    session_name = models.CharField(max_length=255, verbose_name="セッション名")
    collection_type = models.CharField(
        max_length=10,
        choices=[('auto', '自動'), ('manual', '手動')],
        verbose_name="収集タイプ"
    )
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="開始時間")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="終了時間")
    image_count = models.IntegerField(default=0, verbose_name="収集画像数")
    notes = models.TextField(blank=True, verbose_name="メモ")
    
    class Meta:
        verbose_name = "データ収集セッション"
        verbose_name_plural = "データ収集セッション"
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.project.name} - {self.session_name}"
