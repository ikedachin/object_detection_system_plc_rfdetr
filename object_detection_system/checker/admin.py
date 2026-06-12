from django.contrib import admin
from .models import InferenceResult, DetectedObject

# Register your models here.

class DetectedObjectInline(admin.TabularInline):
    """検出オブジェクトをインライン表示"""
    model = DetectedObject
    extra = 0
    fields = ('class_name', 'confidence', 'bbox_center_x', 'bbox_center_y', 'bbox_width', 'bbox_height')


@admin.register(InferenceResult)
class InferenceResultAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'project', 'training_run', 'model_name', 'total_objects_count', 'image_width', 'image_height')
    list_filter = ('project', 'training_run', 'created_at')
    search_fields = ('project__name', 'training_run__training_name', 'model_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    inlines = [DetectedObjectInline]
    
    fieldsets = (
        ('基本情報', {
            'fields': ('project', 'training_run', 'model_name')
        }),
        ('画像情報', {
            'fields': ('result_image_path', 'image_width', 'image_height')
        }),
        ('推論結果', {
            'fields': ('detected_class_summary', 'total_objects_count', 'inference_config')
        }),
        ('システム情報', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(DetectedObject)
class DetectedObjectAdmin(admin.ModelAdmin):
    list_display = ('inference_result', 'class_name', 'confidence', 'bbox_center_x', 'bbox_center_y', 'bbox_width', 'bbox_height')
    list_filter = ('class_name', 'inference_result__project', 'inference_result__created_at')
    search_fields = ('class_name', 'inference_result__project__name')
