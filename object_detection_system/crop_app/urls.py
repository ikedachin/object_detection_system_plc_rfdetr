from django.urls import path
from . import views

urlpatterns = [
    # メイン画面
    path('', views.crop_tool, name='crop_tool'),
    
    # プロジェクト関連
    path('api/create-crop-session/', views.create_crop_session, name='create_crop_session'),
    path('api/get-session-images/', views.get_session_images, name='get_session_images'),
    path('api/add-crop-image/', views.add_crop_image, name='add_crop_image'),
    path('api/save-crop-area/', views.save_crop_area, name='save_crop_area'),
    path('api/get-project-sessions/', views.get_project_sessions, name='get_project_sessions'),
    path('api/get-crop-templates/', views.get_crop_templates, name='get_crop_templates'),
    path('api/get-project-image/', views.get_project_image, name='get_project_image'),
    # プロジェクト選択関連API（統合版）
    path('api/get-projects-list/', views.get_projects_list, name='get_projects_list'),
    path('api/get-project-folders/', views.get_project_folders, name='get_project_folders'),
    
    # 既存のAPI（下位互換性）
    path('browse-images/', views.browse_images, name='browse_images'),
    path('process-crop/', views.process_crop, name='process_crop'),
    path('process-batch-crop/', views.process_batch_crop, name='process_batch_crop'),
    path('save-bounding-box-yaml/', views.save_bounding_box_yaml, name='save_bounding_box_yaml'),
    path('upload-image/', views.upload_image, name='upload_image'),
    
    # 包括座標での全画像切り抜き
    path('api/process-global-bbox-crop/', views.process_global_bbox_crop, name='process_global_bbox_crop'),

    # 新: 一括切り抜き＆cropped保存
    path('api/crop-and-save-all/', views.crop_and_save_all, name='crop_and_save_all'),
]
