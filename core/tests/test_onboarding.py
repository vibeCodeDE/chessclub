"""Tests für den geführten Onboarding-Assistenten (PRD S7.5, US1, T008)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from core.models import AuditLog, ClubProfile, ModuleSettings, OnboardingProgress
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, MITGLIED_GROUP
from dues.models import FeeCategory

User = get_user_model()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username="vorstand_test", password="password123")
    admin_grp, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    user.groups.add(admin_grp)
    return user


@pytest.fixture
def kapitaen_user(db):
    user = User.objects.create_user(username="kapitaen_test", password="password123")
    kap_grp, _ = Group.objects.get_or_create(name=KAPITAEN_GROUP)
    user.groups.add(kap_grp)
    return user


@pytest.fixture
def mitglied_user(db):
    user = User.objects.create_user(username="mitglied_test", password="password123")
    mit_grp, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)
    user.groups.add(mit_grp)
    return user


@pytest.mark.django_db
class TestOnboardingAccess:
    """Berechtigungstests gemäß PRD §3.8: Nur Admin-Gruppe darf Onboarding nutzen."""

    def test_anonymous_redirected_to_login(self, client):
        url = reverse("core:onboarding_wizard")
        response = client.get(url)
        assert response.status_code == 302
        assert "/anmelden/" in response.url

    def test_mitglied_forbidden(self, client, mitglied_user):
        client.force_login(mitglied_user)
        response = client.get(reverse("core:onboarding_wizard"))
        assert response.status_code == 403

    def test_kapitaen_forbidden(self, client, kapitaen_user):
        client.force_login(kapitaen_user)
        response = client.get(reverse("core:onboarding_wizard"))
        assert response.status_code == 403

    def test_admin_allowed(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse("core:onboarding_wizard"))
        assert response.status_code in {200, 302}


@pytest.mark.django_db
class TestOnboardingWorkflow:
    """Prüfung des schrittweisen Durchlaufs (Schritte 1, 2, 3 und 6)."""

    def test_step_1_profile_save_and_advance(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("core:onboarding_step_1")
        response = client.get(url)
        assert response.status_code == 200

        data = {
            "name": "Schachclub Springer Musterstadt e.V.",
            "kurzname": "SC Springer",
            "zps_nummer": "C0101",
            "kontakt_email": "kontakt@sc-springer.de",
            "gruendungsjahr": "1950",
            "ort": "Musterstadt",
            "spiellokal": "Vereinsheim, Schachweg 1",
            "spielabend_zeiten": "Freitags ab 19:30 Uhr",
            "jugend_zeiten": "Freitags ab 17:30 Uhr",
            "beschreibung": "Ein traditionsreicher Schachverein.",
        }
        post_response = client.post(url, data=data)
        assert post_response.status_code == 302
        assert post_response.url == reverse("core:onboarding_step_2")

        # Prüfe Persistierung im ClubProfile
        club = ClubProfile.get_solo()
        assert club.name == "Schachclub Springer Musterstadt e.V."
        assert club.zps_nummer == "C0101"

        # Prüfe Status
        progress = OnboardingProgress.get_solo()
        assert progress.aktueller_schritt == 2
        assert "profil" in progress.schritte_abgeschlossen

    def test_step_1_validation_error(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("core:onboarding_step_1")
        # Fehlender Vereinsname
        data = {
            "name": "",
            "kurzname": "SC Springer",
            "kontakt_email": "ungueltige-email",
        }
        response = client.post(url, data=data)
        assert response.status_code == 200
        assert "name" in response.context["form"].errors

    def test_step_2_modules_save(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("core:onboarding_step_2")
        data = {
            "homepage_aktiv": "on",
            "spielbetrieb_aktiv": "on",
            "turniere_aktiv": "on",
            "kassenbuch_aktiv": "on",
            # nachrichten_aktiv ausgelassen = False
        }
        response = client.post(url, data=data)
        assert response.status_code == 302
        assert response.url == reverse("core:onboarding_step_3")

        modules = ModuleSettings.get_solo()
        assert modules.homepage_aktiv is True
        assert modules.spielbetrieb_aktiv is True
        assert modules.turniere_aktiv is True
        assert modules.kassenbuch_aktiv is True
        assert modules.nachrichten_aktiv is False

        progress = OnboardingProgress.get_solo()
        assert "module" in progress.schritte_abgeschlossen
        assert progress.aktueller_schritt == 3

    def test_step_3_apply_default_fee_categories(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("core:onboarding_step_3")
        assert FeeCategory.objects.count() == 0

        # Vorlagen übernehmen
        response = client.post(url, data={"action": "apply_defaults"})
        assert response.status_code == 302
        assert FeeCategory.objects.count() >= 4
        assert FeeCategory.objects.filter(name__icontains="Erwachsene").exists()

        # AuditLog geprüft
        assert AuditLog.objects.filter(aktion__icontains="Beitrag").exists()

    def test_step_3_advance(self, client, admin_user):
        from dues.models import FeeAmount

        client.force_login(admin_user)
        url = reverse("core:onboarding_step_3")
        cat = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=cat, jahr=2026, betrag=60)

        response = client.post(url, data={"action": "next"})
        assert response.status_code == 302
        assert response.url == reverse("core:onboarding_step_4")

        progress = OnboardingProgress.get_solo()
        assert "beitraege" in progress.schritte_abgeschlossen

    def test_step_6_finish(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("core:onboarding_step_6")
        response = client.get(url)
        assert response.status_code == 200

        # Abschluss
        post_response = client.post(url, data={"action": "complete"})
        assert post_response.status_code == 302
        assert post_response.url == reverse("core:dashboard")

        progress = OnboardingProgress.get_solo()
        assert progress.ist_abgeschlossen is True
        assert progress.abgeschlossen_von == admin_user
        assert progress.abgeschlossen_am is not None

        # AuditLog
        assert AuditLog.objects.filter(aktion__icontains="Onboarding").exists()


@pytest.mark.django_db
class TestOnboardingLoginRedirect:
    """Prüfung des automatischen Erst-Redirects nach dem Login."""

    def test_new_admin_redirected_to_onboarding_if_club_empty(self, client, admin_user):
        # Profil ist noch leer
        club = ClubProfile.get_solo()
        club.name = ""
        club.save()
        progress = OnboardingProgress.get_solo()
        progress.ist_abgeschlossen = False
        progress.save()

        response = client.post(
            reverse("core:login"),
            {"username": "vorstand_test", "password": "password123"},
        )
        # Sollte nach /onboarding/ leiten (bzw. 2FA falls aktiv)
        assert response.status_code == 302
        assert response.url in {reverse("core:onboarding_wizard"), reverse("core:zwei_faktor")}

    def test_dashboard_renders_with_onboarding_widget_if_unconfigured(self, client, admin_user):
        client.force_login(admin_user)
        club = ClubProfile.get_solo()
        club.name = ""
        club.save()
        progress = OnboardingProgress.get_solo()
        progress.ist_abgeschlossen = False
        progress.save()

        response = client.get(reverse("core:dashboard"))
        assert response.status_code == 200
        assert response.context["onboarding_widget"] is not None
        assert response.context["onboarding_widget"]["sichtbar"] is True
