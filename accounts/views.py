from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import (
    LoginForm,
    SignupForm,
    ProfileForm,
    SettingsForm,
    DataSentinelPasswordChangeForm,
)
from .models import UserSettings


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_page")

    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = None

            try:
                existing_user = User.objects.get(
                    email__iexact=email
                )

                user = authenticate(
                    request,
                    username=existing_user.username,
                    password=password,
                )

            except User.DoesNotExist:
                user = None

            if user is not None:
                login(
                    request,
                    user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )

                next_url = request.GET.get("next")

                if next_url:
                    return redirect(next_url)

                return redirect("dashboard_page")

            form.add_error(
                None,
                "Invalid email or password.",
            )

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
        },
    )


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_page")

    form = SignupForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password1"]

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
            )

            UserSettings.objects.create(
                user=user
            )

            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )

            messages.success(
                request,
                "Your DataSentinel account has been created successfully.",
            )

            return redirect("dashboard_page")

    return render(
        request,
        "accounts/signup.html",
        {
            "form": form,
        },
    )


def logout_view(request):
    if request.method == "POST":
        logout(request)

    return redirect("login")


def profile_view(request):
    if not request.user.is_authenticated:
        return redirect("login")

    form = ProfileForm(
        request.POST or None,
        instance=request.user,
    )

    if request.method == "POST":
        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Your profile has been updated successfully.",
            )

            return redirect("profile")

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
        },
    )


def settings_view(request):
    if not request.user.is_authenticated:
        return redirect("login")

    settings_obj, created = UserSettings.objects.get_or_create(
        user=request.user
    )

    settings_form = SettingsForm(
        request.POST or None,
        instance=settings_obj,
    )

    password_form = DataSentinelPasswordChangeForm(
        request.user
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_settings":
            settings_form = SettingsForm(
                request.POST,
                instance=settings_obj,
            )

            if settings_form.is_valid():
                settings_form.save()

                messages.success(
                    request,
                    "Your settings have been saved successfully.",
                )

                return redirect("settings")

        elif action == "change_password":
            password_form = DataSentinelPasswordChangeForm(
                request.user,
                request.POST,
            )

            if password_form.is_valid():
                password_form.save()

                messages.success(
                    request,
                    "Your password has been changed successfully.",
                )

                return redirect("settings")

    return render(
        request,
        "accounts/settings.html",
        {
            "settings_form": settings_form,
            "password_form": password_form,
        },
    )