from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'annotator'

urlpatterns = [
    path('', views.index, name='index'),
    path('projects/', views.project, name='project'),
    path('annotate/<int:image_id>/<str:cropped>/', views.annotate, name='annotate'),
    path('api/save_annotations/<int:image_id>/', views.save_annotations, name='save_annotations'),
    path('api/load_images/', views.load_images, name='load_images'),
    path('api/split_dataset/', views.split_dataset, name='split_dataset'),
    path('api/add_label/', views.add_label, name='add_label'),
    path('api/labels/', views.add_label, name='create_label'),
    path('api/labels/<int:label_id>/', views.update_label, name='update_label'),
    path('api/update_label/<int:label_id>/', views.update_label, name='update_label_alt'),
    path('api/delete_label/<int:label_id>/', views.delete_label, name='delete_label'),
    path('api/set_active_label/', views.set_active_label, name='set_active_label'),
    path('api/set_active_project/<int:project_id>/', views.set_active_project, name='set_active_project'),
    path('api/scan_projects/', views.scan_projects, name='scan_projects'),
    path('api/load_project_images/<int:project_id>/', views.load_project_images, name='load_project_images'),
    path('images/<str:filename>', views.serve_image, name='serve_image'),
    path('get_thumbnail/<int:image_id>/<str:cropped>/', views.get_thumbnail, name='get_thumbnail'),
]

# 開発環境での画像ファイル配信
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     # base_images フォルダの画像を配信
#     urlpatterns += static('/base_images/', document_root=settings.BASE_IMAGES_DIR)
