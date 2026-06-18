from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat_home'),
    path('chat/new/', views.create_chat, name='chat_create'),
    path('chat/<int:branch_id>/', views.chat_view, name='chat_detail'),
    path('chat/<int:branch_id>/stream/', views.stream_message, name='chat_stream'),
    path('chat/<int:branch_id>/edit/', views.edit_chat, name='chat_edit'),
    path('chat/<int:branch_id>/delete/', views.delete_chat, name='chat_delete'),
    path('branch/<int:branch_id>/delete-messages/', views.delete_all_messages, name='delete_all_messages'),
]