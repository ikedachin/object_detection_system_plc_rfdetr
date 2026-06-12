from django.contrib import admin
from .models import DataCollectionProject, DataCollectionSession

# Register your models here.

@admin.register(DataCollectionProject)
class DataCollectionProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'folder_name', 'total_image_count', 'auto_image_count', 'manual_image_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'folder_name', 'description')
    readonly_fields = ('created_at', 'auto_image_count', 'manual_image_count', 'total_image_count')
    actions = ['make_active', 'update_image_counts']
    
    def make_active(self, request, queryset):
        """選択したプロジェクトをアクティブにする"""
        for project in queryset:
            project.set_active()
            break  # 一つだけアクティブにする
        self.message_user(request, f"{queryset.first().name} をアクティブプロジェクトに設定しました。")
    make_active.short_description = "選択したプロジェクトをアクティブにする"
    
    def update_image_counts(self, request, queryset):
        """画像数を更新"""
        for project in queryset:
            project.update_image_counts()
        self.message_user(request, f"{queryset.count()} プロジェクトの画像数を更新しました。")
    update_image_counts.short_description = "画像数を更新"


@admin.register(DataCollectionSession)
class DataCollectionSessionAdmin(admin.ModelAdmin):
    list_display = ('session_name', 'project', 'collection_type', 'image_count', 'start_time', 'end_time')
    list_filter = ('collection_type', 'start_time', 'project')
    search_fields = ('session_name', 'project__name', 'notes')
    readonly_fields = ('start_time',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')
