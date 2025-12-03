
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # create session
    path('create/', views.create_session, name='create_session'),
    path('session/<str:code>/', views.session_detail, name='session_detail'),

    # connect to session
    path('join/', views.join_session, name='join_session'),
    path('join/<str:code>/device/', views.join_session_device, name='join_session_device'),
    path('join/<str:code>/connected/', views.join_connected, name='join_connected'),


    # mic connect

    path('mic/<int:pk>/', views.mic_detail, name='mic_detail'),
    path('mic/<int:pk>/ready', views.mic_ready, name='mic_ready'),

    # recording
    path('session/<str:code>/start/', views.start_recording, name='start_recording'),

]
