from django.urls import path
from . import views

urlpatterns = [
    path('', views.train_view, name='training_index'),  # 学習実行
    path('management/', views.training_management_view, name='training_management'),  # 学習管理
]
