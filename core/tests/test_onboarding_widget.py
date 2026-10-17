"""Tests für das Dashboard-Widget 'Erste Schritte' (US3, T019)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from core.models import AuditLog, ClubProfile, OnboardingProgress, StaffInvitation
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, MITGLIED_GROUP
from core.services import get_onboarding_checklist_status
from dues.models import FeeCategory
from members.models import Member
from teams.models import Team

User = get_user_model()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username="admin_widget", password="password123")
    grp, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    user.groups.add(grp)
    return user


@pytest.fixture
def kapitaen_user(db):
    user = User.objects.create_user(username="kapitaen_widget", password="password123")
    grp, _ = Group.objects.get_or_create(name=KAPITAEN_GROUP)
    user.groups.add(grp)
    return user


@pytest.fixture
def mitglied_user(db):
    user = User.objects.create_user(username="mitglied_widget", password="password123")
    grp, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)
    user.groups.add(grp)
    return user


@pytest.mark.django_db
class TestOnboardingChecklistService:
    def test_checklist_initial_calculation(self):
        club = ClubProfile.get_solo()
        club.name = ""
        club.kontakt_email = ""
        club.save()

        status = get_onboarding_checklist_status()
        assert status["sichtbar"] is True
        assert status["gesamt_schritte"] == 5
        assert status["erledigte_schritte"] == 0
        assert status["fortschritt_prozent"] == 0

    def test_checklist_with_completed_items(self, admin_user):
        club = ClubProfile.get_solo()
        club.name = "SC Schachfreunde"
        club.kontakt_email = "info@schachfreunde.de"
        club.save()

        FeeCategory.objects.create(name="Erwachsene", aktiv=True)
        Member.objects.create(
            vorname="Max",
            nachname="Mustermann",
            eintrittsdatum="2026-01-01",
            status="aktiv",
        )

        status = get_onboarding_checklist_status()
        assert status["sichtbar"] is True
        assert status["erledigte_schritte"] == 3  # Profil, Beiträge, Mitglieder
        assert status["fortschritt_prozent"] == 60

    def test_checklist_hidden_when_dismissed(self):
        progress = OnboardingProgress.get_solo()
        progress.checklist_ausgeblendet = True
        progress.save()

        status = get_onboarding_checklist_status()
        assert status["sichtbar"] is False
        assert status["fortschritt_prozent"] == 0

    def test_query_count_is_minimal(self, django_assert_num_queries):
        # Initial call to ensure table caches or initial setup if any
        get_onboarding_checklist_status()
        with django_assert_num_queries(7):
            get_onboarding_checklist_status()


@pytest.mark.django_db
class TestOnboardingWidgetDashboardView:
    def test_admin_sees_widget_on_dashboard(self, client, admin_user):
        progress = OnboardingProgress.get_solo()
        progress.ist_abgeschlossen = True
        progress.checklist_ausgeblendet = False
        progress.save()

        client.force_login(admin_user)
        response = client.get(reverse("core:dashboard"))
        assert response.status_code == 200
        assert "Erste Schritte" in response.content.decode("utf-8")
        assert "onboarding-checklist" in response.content.decode("utf-8")

    def test_admin_widget_hidden_if_dismissed(self, client, admin_user):
        progress = OnboardingProgress.get_solo()
        progress.ist_abgeschlossen = True
        progress.checklist_ausgeblendet = True
        progress.save()

        client.force_login(admin_user)
        response = client.get(reverse("core:dashboard"))
        assert response.status_code == 200
        assert "onboarding-checklist" not in response.content.decode("utf-8")

    def test_kapitaen_never_sees_widget(self, client, kapitaen_user):
        progress = OnboardingProgress.get_solo()
        progress.ist_abgeschlossen = True
        progress.checklist_ausgeblendet = False
        progress.save()

        client.force_login(kapitaen_user)
        response = client.get(reverse("core:dashboard"))
        assert response.status_code == 200
        assert "onboarding-checklist" not in response.content.decode("utf-8")

    def test_mitglied_never_sees_widget(self, client, mitglied_user):
        progress = OnboardingProgress.get_solo()
        progress.ist_abgeschlossen = True
        progress.checklist_ausgeblendet = False
        progress.save()

        client.force_login(mitglied_user)
        response = client.get(reverse("core:dashboard"))
        assert response.status_code == 200
        assert "onboarding-checklist" not in response.content.decode("utf-8")


@pytest.mark.django_db
class TestOnboardingDismissChecklistView:
    def test_admin_can_dismiss_checklist(self, client, admin_user):
        progress = OnboardingProgress.get_solo()
        progress.checklist_ausgeblendet = False
        progress.save()

        client.force_login(admin_user)
        url = reverse("core:onboarding_checklist_dismiss")
        response = client.post(url)
        assert response.status_code == 302
        assert response.url == reverse("core:dashboard")

        progress.refresh_from_db()
        assert progress.checklist_ausgeblendet is True

        # AuditLog entry
        assert AuditLog.objects.filter(aktion="Onboarding-Checkliste ausgeblendet").exists()

    def test_ajax_dismiss(self, client, admin_user):
        progress = OnboardingProgress.get_solo()
        progress.checklist_ausgeblendet = False
        progress.save()

        client.force_login(admin_user)
        url = reverse("core:onboarding_checklist_dismiss")
        response = client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert response.status_code == 200
        assert response.json() == {"erfolg": True}

        progress.refresh_from_db()
        assert progress.checklist_ausgeblendet is True

    def test_mitglied_cannot_dismiss_checklist(self, client, mitglied_user):
        client.force_login(mitglied_user)
        url = reverse("core:onboarding_checklist_dismiss")
        response = client.post(url)
        assert response.status_code == 403
