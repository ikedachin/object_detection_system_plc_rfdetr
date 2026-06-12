from django.urls import path
from . import views

urlpatterns = [
    # path('', views.index, name='index'),  # Main page of the get_imgs app
    path('', views.index, name='index'),  # Endpoint to check inventory
    path('collect', views.get_imgs, name='collect'),  # Endpoint to get images
    path('api/create_project_folders', views.create_project_folders, name='create_project_folders'),
    path('api/set_active_project', views.set_active_project, name='set_active_project'),
    path('api/get_project_stats', views.get_project_stats, name='get_project_stats'),
    path('api/create_collection_session', views.create_collection_session, name='create_collection_session'),
    path('api/get_camera_availability', views.get_camera_availability, name='get_camera_availability'),
    path('api/test_camera_connection', views.test_camera_connection, name='test_camera_connection'),
]
