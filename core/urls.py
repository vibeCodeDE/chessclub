from django.contrib.auth import views as django_auth_views
from django.urls import path

from . import auth_views, views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("produkt/", views.produkt_seite, name="produkt"),
    path("impressum/", views.rechtliches, {"seite": "impressum"}, name="impressum"),
    path("datenschutz/", views.rechtliches, {"seite": "datenschutz"}, name="datenschutz"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("verein/", views.verein, name="verein"),
    path("aktuelles/", views.news_archiv, name="news_archiv"),
    path("aktuelles/<int:pk>/", views.news_detail, name="news_detail"),
    path("suche/", views.suche, name="suche"),
    path("audit/", views.audit_list, name="audit_list"),
    path("health/", views.health, name="health"),
    path("offline/", views.offline, name="offline"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("mitglieder/<int:pk>/auskunft/", views.dsgvo_auskunft, name="dsgvo_auskunft"),
    path("mitglieder/<int:pk>/auskunft.pdf", views.dsgvo_pdf, name="dsgvo_pdf"),
    path("mitglieder/<int:pk>/auskunft.json", views.dsgvo_export, name="dsgvo_export"),
    path("datenschutz/verzeichnis.csv", views.dsgvo_verzeichnis, name="dsgvo_verzeichnis"),
    path("anmelden/", auth_views.anmelden, name="login"),
    path("anmelden/zwei-faktor/", auth_views.zwei_faktor, name="zwei_faktor"),
    path("anmelden/zwei-faktor/neu/", auth_views.zwei_faktor_neu, name="zwei_faktor_neu"),
    path("abmelden/", django_auth_views.LogoutView.as_view(), name="logout"),
    path(
        "passwort/aendern/",
        django_auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            success_url="/passwort/aendern/fertig/",
        ),
        name="password_reset",
    ),
    path(
        "passwort/aendern/fertig/",
        django_auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "passwort/aendern/<uidb64>/<token>/",
        django_auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url="/passwort/aendern/bestaetigt/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "passwort/aendern/bestaetigt/",
        django_auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
