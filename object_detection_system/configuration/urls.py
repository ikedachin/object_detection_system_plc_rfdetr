from django.urls import path
from . import views

app_name = 'configuration'

urlpatterns = [
    path('', views.configuration, name='configuration'),  # インベントリ確認エンドポイント
    path('configuration', views.configuration, name='configuration'),  # インベントリ確認エンドポイント
    path('crop/', views.crop_redirect, name='crop'),  # 切り抜きアプリへのリダイレクト
    path('browse-images/', views.browse_images, name='browse_images'),  # ファイル参照用
    path('workflow-manager/', views.workflow_manager, name='workflow_manager'),  # ワークフロー管理画面
    path('change-workflow/', views.change_workflow, name='change_workflow'),  # ワークフロー変更
    # プロジェクト管理
    path('project-manager/', views.project_manager, name='project_manager'),  # プロジェクト管理画面
    path('add-project/', views.add_project, name='add_project'),  # プロジェクト追加API
    path('delete-project/', views.delete_project, name='delete_project'),  # プロジェクト削除API
    path('get-project-info/', views.get_project_info, name='get_project_info'),  # プロジェクト情報取得API
    path('set-active-project/', views.set_active_project, name='set_active_project'),  # プロジェクトアクティブ化API
]

