
from django.db import models
from django.core.exceptions import ValidationError
from annotator.models import Project

class TrainingRun(models.Model):
    # Augmentation parameters
    flipud = models.FloatField(default=0.0, blank=True, help_text="上下反転確率 (flipud)")
    fliplr = models.FloatField(default=0.5, blank=True, help_text="左右反転確率 (fliplr)")
    mixup = models.FloatField(default=0.0, blank=True, help_text="MixUp合成率 (mixup)")
    perspective = models.FloatField(default=0.0, blank=True, help_text="遠近変換強度 (perspective)")
    shear = models.FloatField(default=0.0, blank=True, help_text="シアー強度 (shear)")
    scale = models.FloatField(default=0.5, blank=True, help_text="スケール変換範囲 (scale)")
    PROJECT_DATA_CHOICES = [
        ("data_collection", "data_collection"),
        ("cropped", "cropped"),
    ]

    # 変更: project_nameをProjectのForeignKeyに変更、training_nameを追加
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='training_runs', verbose_name="プロジェクト")
    training_name = models.CharField(max_length=255, verbose_name="学習名", help_text="デフォルト: プロジェクト名_学習年月日_時分秒")
    data_type = models.CharField(max_length=32, choices=PROJECT_DATA_CHOICES)
    dataset_yaml = models.CharField(max_length=512)
    model_name = models.CharField(max_length=255)
    epochs = models.PositiveIntegerField(default=100)
    imgsz = models.CharField(max_length=32, default="640")
    batch = models.PositiveIntegerField(default=16)
    other_params = models.JSONField(default=dict, blank=True)
    trained_at = models.DateTimeField(auto_now_add=True)
    saved_model_path = models.CharField(max_length=512, blank=True)
    config_yaml_path = models.CharField(max_length=512, blank=True, help_text="設定用YAMLファイルのパス（推論・検出共通）")
    metrics = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False, help_text="現在アクティブな学習モデル")

    class Meta:
        unique_together = ('project', 'training_name')
        constraints = [
            models.UniqueConstraint(
                fields=['project'],
                condition=models.Q(is_active=True),
                name='unique_active_training_per_project'
            )
        ]

    def clean(self):
        # is_activeが複数Trueにならないようにバリデーション
        if self.is_active:
            existing_active = TrainingRun.objects.filter(
                project=self.project, 
                is_active=True
            ).exclude(pk=self.pk)
            if existing_active.exists():
                raise ValidationError('1つのプロジェクトにつき、アクティブな学習モデルは1つだけです。')

    def save(self, *args, **kwargs):
        # is_activeがTrueの場合、同じプロジェクトの他の学習を非アクティブにする
        if self.is_active:
            TrainingRun.objects.filter(
                project=self.project, 
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project.name} - {self.training_name} ({self.data_type}) - {self.trained_at.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def get_active_training(cls, project):
        """指定されたプロジェクトのアクティブな学習を取得"""
        return cls.objects.filter(project=project, is_active=True).first()

    def set_active(self):
        """この学習をアクティブにする"""
        TrainingRun.objects.filter(project=self.project).update(is_active=False)
        self.is_active = True
        self.save()

    @property
    def model_folder_path(self):
        """学習モデルのフォルダパスを返す"""
        from django.conf import settings
        import os
        return os.path.join(settings.PROJECTS_DIR, self.project.folder_name, 'models', self.training_name)

    def generate_default_training_name(self):
        """デフォルトの学習名を生成"""
        from datetime import datetime
        now = datetime.now()
        return f"{self.project.name}_{now.strftime('%Y%m%d_%H%M%S')}"
