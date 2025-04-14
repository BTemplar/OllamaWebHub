from django.urls import path
from . import views

urlpatterns = [
    path('chat_branches/', views.chat_branch_list, name='chat_branch_list'),
    path('chat_branches/create/', views.chat_branch_create, name='chat_branch_create'),
    path('chat_branches/<int:pk>/delete/', views.chat_branch_delete, name='chat_branch_delete'),
    path('chat/<int:pk>/', views.chat_view, name='chat_view'),
    path('chat/<int:pk>/send/', views.send_message, name='send_message'),
]