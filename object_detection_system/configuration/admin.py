from django.contrib import admin
from .models import WorkflowSetting, TaskProgress, ProjectTaskProgress, ProjectWorkflowState

# Register your models here.

@admin.register(WorkflowSetting)
class WorkflowSettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'workflow_type', 'is_active', 'created_at')
    list_filter = ('workflow_type', 'is_active')
    search_fields = ('name', 'description')
    actions = ['make_active']
    
    def make_active(self, request, queryset):
        """選択した設定をアクティブにする"""
        # 全ての設定を非アクティブにする
        WorkflowSetting.objects.update(is_active=False)
        # 選択した最初の設定をアクティブにする
        queryset.first().is_active = True
        queryset.first().save()
        self.message_user(request, f"{queryset.first().name} をアクティブ設定にしました。")
    make_active.short_description = "選択した設定をアクティブにする"


@admin.register(TaskProgress)
class TaskProgressAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'completed_count', 'image_count', 'progress_percentage', 'last_updated')
    list_filter = ('task_name', 'last_updated')
    readonly_fields = ('last_updated',)


@admin.register(ProjectTaskProgress)
class ProjectTaskProgressAdmin(admin.ModelAdmin):
    list_display = ('project', 'task_name', 'completed_count', 'image_count', 'progress_percentage', 'last_updated')
    list_filter = ('task_name', 'project', 'last_updated')
    search_fields = ('project__name', 'notes')
    readonly_fields = ('last_updated',)
    actions = ['update_progress']
    
    def update_progress(self, request, queryset):
        """進捗を更新"""
        for progress in queryset:
            progress.update_counts()
        self.message_user(request, f"{queryset.count()} 件の進捗を更新しました。")
    update_progress.short_description = "進捗を更新"


@admin.register(ProjectWorkflowState)
class ProjectWorkflowStateAdmin(admin.ModelAdmin):
    list_display = ('project', 'current_task', 'workflow_setting', 'updated_at')
    list_filter = ('current_task', 'workflow_setting', 'updated_at')
    search_fields = ('project__name',)
    readonly_fields = ('created_at', 'updated_at')
    actions = ['advance_to_next_task']
    
    def advance_to_next_task(self, request, queryset):
        """次のタスクに進める"""
        count = 0
        for state in queryset:
            if state.advance_to_next_task():
                count += 1
        self.message_user(request, f"{count} 件のプロジェクトを次のタスクに進めました。")
    advance_to_next_task.short_description = "次のタスクに進める"
