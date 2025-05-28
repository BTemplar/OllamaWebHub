from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat_home'),
    path('chat/new/', views.create_chat, name='chat_create'),
    path('chat/<int:branch_id>/', views.chat_view, name='chat_detail'),
    path('chat/rename/<int:branch_id>/', views.rename_chat, name='chat_rename'),
    path('chat/<int:branch_id>/delete/', views.delete_chat, name='chat_delete'),
    path('branch/<int:branch_id>/delete-messages/', views.delete_all_messages, name='delete_all_messages'),
]