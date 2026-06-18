# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from .forms import LoginForm, SignUpForm


def login_view(request: HttpRequest) -> HttpResponse:
    """
    Display the login form and authenticate the user.

    Args:
        request (HttpRequest): Current HTTP request.

    Returns:
        HttpResponse: Redirect to chat home on success or rendered login page.
    """
    if request.user.is_authenticated:
        return redirect("chat_home")

    form = LoginForm(request.POST or None)
    msg = None

    if request.method == "POST":
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                return redirect("chat_home")
            msg = "Incorrect credentials entered"
        else:
            msg = "Form validation error"

    return render(request, "accounts/login.html", {"form": form, "msg": msg})


def register_user(request: HttpRequest) -> HttpResponse:
    """
    Register a new user when public registration is enabled.

    Args:
        request (HttpRequest): Current HTTP request.

    Returns:
        HttpResponse: Redirect on success, rendered registration page, or 404.

    Raises:
        Http404: If public registration is disabled in settings.
    """
    if not settings.REGISTRATION_ENABLED:
        raise Http404()

    if request.user.is_authenticated:
        return redirect("chat_home")

    msg = None
    success = False

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            user = authenticate(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
            )
            if user is not None:
                login(request, user)
                return redirect("chat_home")
            msg = f'User created. <a href="/login/">Sign in as {form.cleaned_data["username"]}</a>.'
            success = True
        else:
            msg = "The form is invalid"
    else:
        form = SignUpForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form, "msg": msg, "success": success},
    )
