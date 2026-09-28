from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("health/", views.health, name="health"),
    path(
        "anmelden/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("abmelden/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "passwort/aendern/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            success_url="/passwort/aendern/fertig/",
        ),
        name="password_reset",
    ),
    path(
        "passwort/aendern/fertig/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "passwort/aendern/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url="/passwort/aendern/bestaetigt/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "passwort/aendern/bestaetigt/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
