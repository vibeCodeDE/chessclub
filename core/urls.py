from django.contrib.auth import views as django_auth_views
from django.urls import path

from . import auth_views, views, views_onboarding, views_setup

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("onboarding/", views_onboarding.onboarding_wizard_entry, name="onboarding_wizard"),
    path("onboarding/schritt/1/", views_onboarding.onboarding_step_1_profile, name="onboarding_step_1"),
    path("onboarding/schritt/2/", views_onboarding.onboarding_step_2_modules, name="onboarding_step_2"),
    path("onboarding/schritt/3/", views_onboarding.onboarding_step_3_dues, name="onboarding_step_3"),
    path("onboarding/schritt/4/", views_onboarding.onboarding_step_4_members, name="onboarding_step_4"),
    path("onboarding/schritt/5/", views_onboarding.onboarding_step_5_staff, name="onboarding_step_5"),
    path("onboarding/schritt/6/", views_onboarding.onboarding_step_6_finish, name="onboarding_step_6"),
    path("onboarding/zurueck/<int:schritt>/", views_onboarding.onboarding_step_back, name="onboarding_step_back"),
    path("onboarding/checklist/ausblenden/", views_onboarding.dismiss_onboarding_checklist, name="onboarding_checklist_dismiss"),
    path("einladung/<str:token>/", auth_views.accept_invitation, name="accept_invitation"),
    path("produkt/", views.produkt_redirect, name="produkt"),
    path("impressum/", views.rechtliches, {"seite": "impressum"}, name="impressum"),
    path("datenschutz/", views.rechtliches, {"seite": "datenschutz"}, name="datenschutz"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("verein/", views.verein, name="verein"),
    path("verein/setup/", views_setup.club_setup_profile, name="club_setup"),
    path("verein/setup/profil/", views_setup.club_setup_profile, name="club_setup_profile"),
    path("verein/setup/beitraege/", views_setup.club_setup_dues, name="club_setup_dues"),
    path("verein/setup/mannschaften/", views_setup.club_setup_teams, name="club_setup_teams"),
    path("verein/setup/mitglieder-import/", views_setup.club_setup_members_import, name="club_setup_members_import"),
    path("verein/setup/mitglieder-import/muster.csv", views_setup.club_setup_import_muster, name="club_setup_import_muster"),
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
    path("passwort/aendern/", auth_views.password_reset, name="password_reset"),
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
