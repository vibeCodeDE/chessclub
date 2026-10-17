"""Tests für den Übergang von Demo-Daten zu Produktivbetrieb im Onboarding (US4, T023)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from core.models import AuditLog, ClubProfile, OnboardingProgress
from core.roles import ADMIN_GROUP
from core.services import complete_onboarding, get_demo_data_status
from dues.models import FeeCategory
from members.models import Member

User = get_user_model()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username="admin_transition", password="password123")
    grp, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    user.groups.add(grp)
    return user


@pytest.fixture
def demo_environment(db):
    """Erstellt eine typische Demo-Umgebung mit Demo-Usern und Demo-Mitgliedern."""
    demo_user = User.objects.create_user(
        username="vorstand",
        password="password123",
        email="vorstand@example.org",
    )
    Member.objects.create(
        vorname="Demo",
        nachname="Mitglied",
        email="demo@example.org",
        eintrittsdatum="2026-01-01",
        status="aktiv",
    )
    FeeCategory.objects.create(name="Erwachsene", aktiv=True)
    return demo_user


@pytest.mark.django_db
class TestOnboardingDemoTransitionService:
    def test_demo_data_detected(self, demo_environment):
        status = get_demo_data_status()
        assert status["is_active"] is True
        assert status["has_real_data"] is False
        assert status["can_remove"] is True

    def test_complete_onboarding_cleans_demo_data(self, admin_user, demo_environment):
        club = ClubProfile.get_solo()
        club.name = "SC Real Club"
        club.kontakt_email = "info@sc-real.de"
        club.save()

        success = complete_onboarding(user=admin_user, cleanup_demodata=True)
        assert success is True

        # Demo members and users removed
        assert not Member.objects.filter(email="demo@example.org").exists()
        assert not User.objects.filter(username="vorstand").exists()

        # Real club profile preserved
        club.refresh_from_db()
        assert club.name == "SC Real Club"

        # Onboarding marked completed
        progress = OnboardingProgress.get_solo()
        assert progress.ist_abgeschlossen is True
        assert progress.abgeschlossen_von == admin_user

        # AuditLog
        assert AuditLog.objects.filter(aktion="Demo-Daten entfernt").exists()
        assert AuditLog.objects.filter(aktion="Onboarding abgeschlossen").exists()

    def test_real_data_protected_from_deletion(self, admin_user, demo_environment):
        """Negativtest / Schutz vor Datenverlust: Reale Mitglieder dürfen nicht gelöscht werden."""
        real_member = Member.objects.create(
            vorname="Echtes",
            nachname="Mitglied",
            email="echt@meinschachverein.de",  # Reale Vereinsdomain
            eintrittsdatum="2026-02-01",
            status="aktiv",
        )

        status = get_demo_data_status()
        assert status["is_active"] is True
        assert status["has_real_data"] is True
        assert status["can_remove"] is False

        # Versuch der Bereinigung
        success = complete_onboarding(user=admin_user, cleanup_demodata=True)
        assert success is True

        # Reales Mitglied ist weiterhin geschützt vorhanden!
        assert Member.objects.filter(pk=real_member.pk).exists()

        progress = OnboardingProgress.get_solo()
        assert progress.ist_abgeschlossen is True


@pytest.mark.django_db
class TestOnboardingStep6View:
    def test_step_6_view_shows_demo_warning(self, client, admin_user, demo_environment):
        client.force_login(admin_user)
        response = client.get(reverse("core:onboarding_step_6"))
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Demo-Daten sind derzeit geladen" in content
        assert "cleanup_demodata" in content

    def test_step_6_post_executes_cleanup(self, client, admin_user, demo_environment):
        client.force_login(admin_user)
        response = client.post(
            reverse("core:onboarding_step_6"),
            data={"action": "complete", "cleanup_demodata": "1"},
        )
        assert response.status_code == 302
        assert response.url == reverse("core:dashboard")

        # Demo-Daten gelöscht
        assert not Member.objects.filter(email="demo@example.org").exists()

        progress = OnboardingProgress.get_solo()
        assert progress.ist_abgeschlossen is True
