"""
URL configuration for inventry_checker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('get_imgs.urls')),  # Include the app's URLs
    path('annotator/', include('annotator.urls')),  # Include the annotator app's URLs
    path('get_imgs/', include('get_imgs.urls')),  # Include the get_imgs app's URLs
    path('checker/', include('checker.urls')),  # Include the checker app's URLs
    path('configuration/', include('configuration.urls')),  # Include the configuration app's URLs
    path('crop_app/', include('crop_app.urls')),  # Add crop_app URLs
    path('crop/', include('crop_app.urls')),  # Alias for easier access
    path('training/', include('training.urls')),  # Alias for easier access
]

# 開発環境での静的ファイル提供
# if settings.DEBUG:
#     # プロジェクトルートの画像ファイルを提供（BASE_DIR.parentを使用）
#     project_root = settings.BASE_DIR.parent
    
#     # タスク別フォルダの静的ファイル提供
#     # 1. データ収集
#     urlpatterns += static('/data_collection/', document_root=str(settings.DATA_COLLECTION_DIR))
    
#     # 2. 切り抜き準備
#     urlpatterns += static('/crop_preparation/', document_root=str(settings.CROP_PREPARATION_DIR))
    
#     # 3. アノテーション
#     urlpatterns += static('/annotation_data/', document_root=str(settings.ANNOTATION_DATA_DIR))
    
#     # 4. 学習データ
#     urlpatterns += static('/training_data/', document_root=str(settings.TRAINING_DATA_DIR))
    
#     # 5. 実用データ
#     urlpatterns += static('/production_data/', document_root=str(settings.PRODUCTION_DATA_DIR))
    
#     # プロジェクト別フォルダの静的ファイル提供（新構造対応）
#     urlpatterns += static('/projects/', document_root=str(settings.PROJECTS_DIR))
    
#     # 下位互換性のため従来のパスも保持
#     urlpatterns += static('/snaps/', document_root=str(project_root / 'snaps'))
    
#     # base_imagesフォルダの静的ファイル提供（複数のパスパターンに対応）
#     urlpatterns += static('/base_images/', document_root=str(project_root / 'base_images'))
#     urlpatterns += static('/base_images/', document_root=str(settings.BASE_IMAGES_DIR))
    
#     # data_collectionフォルダの直接アクセス
#     urlpatterns += static('/data_collection/', document_root=str(settings.DATA_COLLECTION_DIR))
    
#     # Djangoの標準MEDIA_ROOTも提供
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
