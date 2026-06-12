from django.urls import path
from . import views

urlpatterns = [
    # path('', views.index, name='index'),  # Main page of the checker app
    path('', views.checker_index, name='index'),  # Endpoint to check inventory
    path('checker', views.checker_index, name='checker'),  # Endpoint to get images
    # path('select_project/', views.select_project, name='select_project'),
    # path('api/config_files/', views.get_config_files, name='get_config_files'),
    path('api/get_weight_path/', views.get_weight_path, name='get_weight_path'),
    path('api/set_active_project/', views.set_active_project, name='set_active_project'),
    path('api/set_active_training/', views.set_active_training, name='set_active_training'),
    path('api/load_model/', views.load_model_for_training, name='load_model_for_training'),
    path('api/check_model_status/', views.check_model_status, name='check_model_status'),
    path('api/reset_plc_result/', views.reset_plc_result_signals, name='reset_plc_result_signals'),
]
