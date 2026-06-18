# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import Http404
from django.shortcuts import redirect, render

from .forms import LoginForm, SignUpForm


def login_view(request):
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


def register_user(request):
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
