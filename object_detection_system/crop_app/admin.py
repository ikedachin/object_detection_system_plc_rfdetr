from django.contrib import admin
from .models import CropSession, CropImage, CropArea, CropProgress, CropTemplate


@admin.register(CropSession)
class CropSessionAdmin(admin.ModelAdmin):
    list_display = ('session_name', 'project', 'source_folder', 'total_images', 'processed_images', 'progress_percentage', 'is_completed', 'created_at')
    list_filter = ('is_completed', 'source_folder', 'project', 'created_at')
    search_fields = ('session_name', 'project__name', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'progress_percentage')
    actions = ['update_statistics', 'mark_completed', 'mark_incomplete']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('project', 'session_name', 'source_folder')
        }),
        ('統計情報', {
            'fields': ('total_images', 'processed_images', 'total_crop_areas', 'progress_percentage'),
            'classes': ('collapse',)
        }),
        ('ステータス', {
            'fields': ('is_completed', 'notes')
        }),
        ('タイムスタンプ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def update_statistics(self, request, queryset):
        """統計情報を更新"""
        for session in queryset:
            session.update_statistics()
        self.message_user(request, f"{queryset.count()} セッションの統計を更新しました。")
    update_statistics.short_description = "統計情報を更新"
    
    def mark_completed(self, request, queryset):
        """完了マークを付ける"""
        updated = queryset.update(is_completed=True)
        self.message_user(request, f"{updated} セッションを完了にマークしました。")
    mark_completed.short_description = "完了としてマーク"
    
    def mark_incomplete(self, request, queryset):
        """未完了マークを付ける"""
        updated = queryset.update(is_completed=False)
        self.message_user(request, f"{updated} セッションを未完了にマークしました。")
    mark_incomplete.short_description = "未完了としてマーク"


@admin.register(CropImage)
class CropImageAdmin(admin.ModelAdmin):
    list_display = ('image_name', 'session', 'project_name', 'width', 'height', 'crop_count', 'is_processed', 'upload_date')
    list_filter = ('is_processed', 'session__project', 'session__source_folder', 'upload_date')
    search_fields = ('image_name', 'session__session_name', 'session__project__name')
    readonly_fields = ('upload_date', 'crop_count')
    
    def project_name(self, obj):
        return obj.session.project.name
    project_name.short_description = "プロジェクト名"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session', 'session__project')


@admin.register(CropArea)
class CropAreaAdmin(admin.ModelAdmin):
    list_display = ('crop_image', 'label', 'x', 'y', 'width', 'height', 'confidence', 'has_cropped_image', 'created_at')
    list_filter = ('label', 'crop_image__session__project', 'created_at')
    search_fields = ('label', 'crop_image__image_name', 'crop_image__session__session_name')
    readonly_fields = ('created_at',)
    actions = ['save_cropped_images']
    
    def has_cropped_image(self, obj):
        return bool(obj.cropped_image_path)
    has_cropped_image.boolean = True
    has_cropped_image.short_description = "切り取り済み"
    
    def save_cropped_images(self, request, queryset):
        """選択した領域の切り取り画像を保存"""
        success_count = 0
        for crop_area in queryset:
            if crop_area.save_cropped_image():
                success_count += 1
        self.message_user(request, f"{success_count} / {queryset.count()} の切り取り画像を保存しました。")
    save_cropped_images.short_description = "切り取り画像を保存"


@admin.register(CropProgress)
class CropProgressAdmin(admin.ModelAdmin):
    list_display = ('project', 'total_sessions', 'completed_sessions', 'total_images', 'processed_images', 'progress_percentage', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('project__name',)
    readonly_fields = ('last_updated', 'progress_percentage')
    actions = ['update_progress']
    
    def update_progress(self, request, queryset):
        """進捗を更新"""
        for progress in queryset:
            progress.update_progress()
        self.message_user(request, f"{queryset.count()} プロジェクトの進捗を更新しました。")
    update_progress.short_description = "進捗を更新"


@admin.register(CropTemplate)
class CropTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_name', 'project', 'label', 'width', 'height', 'is_active', 'created_at')
    list_filter = ('is_active', 'project', 'created_at')
    search_fields = ('template_name', 'label', 'project__name', 'description')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('基本情報', {
            'fields': ('project', 'template_name', 'label')
        }),
        ('切り取り設定', {
            'fields': ('width', 'height', 'description')
        }),
        ('ステータス', {
            'fields': ('is_active', 'created_at')
        }),
    )
