from django.contrib import admin
from .models import TrainingRun

@admin.register(TrainingRun)
class TrainingRunAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "training_name", "data_type", "model_name", "epochs", "is_active", "trained_at")
    search_fields = ("project__name", "training_name", "model_name")
    list_filter = ("data_type", "is_active", "trained_at", "project")
    list_editable = ("is_active",)
    readonly_fields = ("trained_at",)
    
    fieldsets = (
        ('基本情報', {
            'fields': ('project', 'training_name', 'data_type', 'is_active')
        }),
        ('学習設定', {
            'fields': ('model_name', 'epochs', 'imgsz', 'batch', 'dataset_yaml')
        }),
        ('ファイルパス', {
            'fields': ('saved_model_path', 'config_yaml_path'),
            'classes': ('collapse',)
        }),
        ('拡張パラメータ', {
            'fields': ('flipud', 'fliplr', 'mixup', 'perspective', 'shear', 'scale', 'other_params'),
            'classes': ('collapse',)
        }),
        ('結果', {
            'fields': ('trained_at', 'metrics'),
            'classes': ('collapse',)
        }),
    )
