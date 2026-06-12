from django.db import models

# Create your models here.

class WorkflowSetting(models.Model):
    """ワークフロー設定"""
    WORKFLOW_CHOICES = [
        ('with_crop', '切り抜きありワークフロー'),
        ('without_crop', '切り抜きなしワークフロー'),
    ]
    
    name = models.CharField(max_length=100, default='default')
    workflow_type = models.CharField(max_length=20, choices=WORKFLOW_CHOICES, default='with_crop')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'ワークフロー設定'
        verbose_name_plural = 'ワークフロー設定'
    
    def __str__(self):
        return f"{self.name} ({self.get_workflow_type_display()})"
    
    @classmethod
    def get_current_workflow(cls):
        """現在アクティブなワークフロー設定を取得"""
        setting = cls.objects.filter(is_active=True).first()
        if not setting:
            # デフォルト設定を作成
            setting = cls.objects.create(
                name='default',
                workflow_type='with_crop',
                description='デフォルトワークフロー設定'
            )
        return setting


class TaskProgress(models.Model):
    """タスク進捗管理"""
    TASK_CHOICES = [
        ('data_collection', 'データ収集'),
        ('crop_preparation', '切り抜き準備'),
        ('annotation', 'アノテーション'),
        ('training', '学習'),
        ('production', '員数確認'),
    ]
    
    task_name = models.CharField(max_length=50, choices=TASK_CHOICES)
    image_count = models.IntegerField(default=0)
    completed_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'タスク進捗'
        verbose_name_plural = 'タスク進捗'
        unique_together = ['task_name']
    
    def __str__(self):
        return f"{self.get_task_name_display()}: {self.completed_count}/{self.image_count}"
    
    @property
    def progress_percentage(self):
        if self.image_count == 0:
            return 0
        return int((self.completed_count / self.image_count) * 100)


class ProjectTaskProgress(models.Model):
    """プロジェクトごとのタスク進捗管理"""
    project = models.ForeignKey('annotator.Project', on_delete=models.CASCADE, related_name='task_progress')
    task_name = models.CharField(max_length=50, choices=TaskProgress.TASK_CHOICES)
    image_count = models.IntegerField(default=0)
    completed_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, verbose_name="メモ")
    
    class Meta:
        verbose_name = 'プロジェクト別タスク進捗'
        verbose_name_plural = 'プロジェクト別タスク進捗'
        unique_together = ['project', 'task_name']
    
    def __str__(self):
        return f"{self.project.name} - {self.get_task_name_display()}: {self.completed_count}/{self.image_count}"
    
    @property
    def progress_percentage(self):
        if self.image_count == 0:
            return 0
        return int((self.completed_count / self.image_count) * 100)
    
    def update_counts(self):
        """タスクの実際の進捗を更新"""
        if self.task_name == 'data_collection':
            # データ収集：プロジェクトの画像数を取得
            self.image_count = self.project.images.count()
            self.completed_count = self.image_count  # 収集済み画像数
        elif self.task_name == 'annotation':
            # アノテーション：アノテーション済み画像数を取得
            self.image_count = self.project.images.count()
            self.completed_count = self.project.images.filter(is_annotated=True).count()
        elif self.task_name == 'crop_preparation':
            # 切り抜き準備：切り抜き済み画像数を取得（実装に応じて調整）
            self.image_count = self.project.images.count()
            # 切り抜き済み画像数の計算ロジックは実装に応じて追加
        elif self.task_name == 'training':
            # 学習：学習データセットの準備状況
            annotated_images = self.project.images.filter(is_annotated=True).count()
            self.image_count = annotated_images
            # 学習データセットの準備完了状況（実装に応じて調整）
        elif self.task_name == 'production':
            # 員数確認：実用段階での処理状況
            pass
        
        self.save()


class ProjectWorkflowState(models.Model):
    """プロジェクトごとのワークフロー状態"""
    project = models.OneToOneField('annotator.Project', on_delete=models.CASCADE, related_name='workflow_state')
    current_task = models.CharField(max_length=50, choices=TaskProgress.TASK_CHOICES, default='data_collection')
    workflow_setting = models.ForeignKey(WorkflowSetting, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'プロジェクトワークフロー状態'
        verbose_name_plural = 'プロジェクトワークフロー状態'
    
    def __str__(self):
        return f"{self.project.name} - {self.get_current_task_display()}"
    
    def get_next_task(self):
        """次のタスクを取得"""
        task_order = ['data_collection', 'crop_preparation', 'annotation', 'training', 'production']
        try:
            current_index = task_order.index(self.current_task)
            if current_index < len(task_order) - 1:
                return task_order[current_index + 1]
        except ValueError:
            pass
        return None
    
    def advance_to_next_task(self):
        """次のタスクに進む"""
        next_task = self.get_next_task()
        if next_task:
            self.current_task = next_task
            self.save()
            return True
        return False
