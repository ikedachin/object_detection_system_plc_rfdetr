from django.contrib import admin
from .models import Project, Label, ImageFile, Annotation


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'folder_name', 'is_active', 'image_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'folder_name')
    readonly_fields = ('created_at', 'image_count')
    actions = ['make_active']
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = "画像数"
    
    def make_active(self, request, queryset):
        """選択したプロジェクトをアクティブにする"""
        for project in queryset:
            project.set_active()
            break  # 一つだけアクティブにする
        self.message_user(request, f"{queryset.first().name} をアクティブプロジェクトに設定しました。")
    make_active.short_description = "選択したプロジェクトをアクティブにする"


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'annotation_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
    
    def annotation_count(self, obj):
        return obj.annotation_set.count()
    annotation_count.short_description = "アノテーション数"


@admin.register(ImageFile)
class ImageFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'project', 'width', 'height', 'is_annotated', 'annotation_count', 'created_at')
    list_filter = ('is_annotated', 'project', 'created_at')
    search_fields = ('filename', 'project__name')
    readonly_fields = ('width', 'height', 'created_at', 'updated_at')
    
    def annotation_count(self, obj):
        return obj.annotations.count()
    annotation_count.short_description = "アノテーション数"


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('image', 'label', 'project_name', 'x_center', 'y_center', 'width', 'height', 'created_at')
    list_filter = ('label', 'created_at', 'image__project')
    search_fields = ('image__filename', 'label__name', 'image__project__name')
    readonly_fields = ('created_at', 'updated_at')
    
    def project_name(self, obj):
        return obj.image.project.name if obj.image.project else "未設定"
    project_name.short_description = "プロジェクト名"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('image', 'label', 'image__project')


# @admin.register(YamlConfig)
# class YamlConfigAdmin(admin.ModelAdmin):
#     list_display = ('project', 'config_name', 'created_at')
#     list_filter = ('project', 'created_at')
#     search_fields = ('config_name', 'project__name')
#     readonly_fields = ('created_at',)


# @admin.register(Weight)
# class WeightAdmin(admin.ModelAdmin):
#     list_display = ('project', 'weight_path', 'created_at')
#     list_filter = ('project', 'created_at')
#     search_fields = ('weight_path', 'project__name')
#     readonly_fields = ('created_at',)
