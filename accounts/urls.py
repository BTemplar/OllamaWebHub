from django.urls import path
from .views import login_view, register_user
from django.contrib.auth.views import LogoutView
from django.urls import reverse_lazy

urlpatterns = [
    path('login/', login_view, name="login"),
    path('register/', register_user, name="register"),
    path('logout/', LogoutView.as_view(next_page=reverse_lazy("login")), name='logout'),
]