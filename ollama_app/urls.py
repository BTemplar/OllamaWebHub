from django.urls import path
from . import views

urlpatterns = [
    # Основные URL
    path('', views.chat_view, name='chat_home'),
    path('chat/new/', views.create_chat, name='chat_create'),
    path('chat/<int:branch_id>/', views.chat_view, name='chat_detail'),

    # Добавьте этот путь для удаления чата
    path('chat/<int:branch_id>/delete/', views.delete_chat, name='chat_delete'),
]