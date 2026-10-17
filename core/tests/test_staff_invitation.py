"""Tests für die Funktionärseinladung per E-Mail & Token (US5, T026)."""

from datetime import timedelta
from unittest.mock import patch
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog, StaffInvitation
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, MITGLIED_GROUP
from core.services import accept_staff_invitation, create_staff_invitation

User = get_user_model()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username="admin_inviter", password="password123")
    grp, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    user.groups.add(grp)
    return user


@pytest.fixture
def mitglied_user(db):
    user = User.objects.create_user(username="mitglied_inviter", password="password123")
    grp, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)
    user.groups.add(grp)
    return user


@pytest.mark.django_db
class TestStaffInvitationService:
    def test_create_staff_invitation_success(self, admin_user):
        invitation = create_staff_invitation(
            email="kasse@sc-muster.de",
            vorname="Klaus",
            nachname="Kasse",
            rolle=ADMIN_GROUP,
            invited_by=admin_user,
            send_mail=True,
            basis_url="https://schachverein.de",
        )

        assert invitation.pk is not None
        assert invitation.token
        assert invitation.status == "offen"
        assert invitation.is_valid is True
        assert invitation.gueltig_bis > timezone.now()

        # E-Mail versendet
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert "kasse@sc-muster.de" in sent_email.to
        assert invitation.token in sent_email.body

        # AuditLog
        assert AuditLog.objects.filter(aktion="Funktionärseinladung erstellt").exists()

    def test_create_revokes_previous_open_invitations(self, admin_user):
        inv1 = create_staff_invitation(
            email="kasse@sc-muster.de",
            vorname="Klaus",
            nachname="Kasse",
            rolle=ADMIN_GROUP,
            invited_by=admin_user,
            send_mail=False,
        )
        assert inv1.status == "offen"

        inv2 = create_staff_invitation(
            email="kasse@sc-muster.de",
            vorname="Klaus",
            nachname="Kasse",
            rolle=KAPITAEN_GROUP,
            invited_by=admin_user,
            send_mail=False,
        )

        inv1.refresh_from_db()
        assert inv1.status == "widerrufen"
        assert inv2.status == "offen"

    def test_accept_staff_invitation_success(self, admin_user):
        invitation = create_staff_invitation(
            email="kapitaen1@sc-muster.de",
            vorname="Karla",
            nachname="Kapt",
            rolle=KAPITAEN_GROUP,
            invited_by=admin_user,
            send_mail=False,
        )

        success, new_user, error = accept_staff_invitation(
            token=invitation.token,
            username="karla_kapitaen",
            password="securePassword123!",
        )

        assert success is True
        assert new_user is not None
        assert "erfolgreich" in error.lower()
        assert new_user.username == "karla_kapitaen"
        assert new_user.groups.filter(name=KAPITAEN_GROUP).exists()

        invitation.refresh_from_db()
        assert invitation.status == "angenommen"
        assert invitation.benutzer == new_user
        assert invitation.angenommen_am is not None

        # AuditLog
        assert AuditLog.objects.filter(aktion="Funktionärseinladung angenommen").exists()

    def test_accept_expired_invitation_fails(self, admin_user):
        """Negativtest: Abgelaufene Einladung kann nicht angenommen werden."""
        invitation = create_staff_invitation(
            email="expired@sc-muster.de",
            vorname="Alt",
            nachname="Mann",
            rolle=ADMIN_GROUP,
            invited_by=admin_user,
            send_mail=False,
        )
        # Ablauf simulieren
        invitation.gueltig_bis = timezone.now() - timedelta(days=1)
        invitation.save()

        success, new_user, error = accept_staff_invitation(
            token=invitation.token,
            username="alt_mann",
            password="securePassword123!",
        )
        assert success is False
        assert new_user is None
        assert "abgelaufen" in error.lower() or "ungültig" in error.lower()

    def test_accept_already_accepted_invitation_fails(self, admin_user):
        """Negativtest: Einladung kann nur einmal angenommen werden."""
        invitation = create_staff_invitation(
            email="once@sc-muster.de",
            vorname="Einmal",
            nachname="Nutzer",
            rolle=ADMIN_GROUP,
            invited_by=admin_user,
            send_mail=False,
        )
        accept_staff_invitation(
            token=invitation.token,
            username="einmal_user",
            password="securePassword123!",
        )

        success, _, error = accept_staff_invitation(
            token=invitation.token,
            username="einmal_user_zwei",
            password="securePassword123!",
        )
        assert success is False
        assert "bereits angenommen" in error.lower()

    def test_accept_duplicate_username_fails(self, admin_user):
        """Negativtest: Doppelter Benutzername wird abgefangen."""
        User.objects.create_user(username="existiert_bereits", password="pw")
        invitation = create_staff_invitation(
            email="neu@sc-muster.de",
            vorname="Neu",
            nachname="User",
            rolle=ADMIN_GROUP,
            invited_by=admin_user,
            send_mail=False,
        )

        success, _, error = accept_staff_invitation(
            token=invitation.token,
            username="existiert_bereits",
            password="securePassword123!",
        )
        assert success is False
        assert "bereits vergeben" in error.lower()


@pytest.mark.django_db
class TestStaffInvitationViews:
    def test_admin_can_access_step_5_and_invite(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse("core:onboarding_step_5"))
        assert response.status_code == 200

        # Post invite
        post_response = client.post(
            reverse("core:onboarding_step_5"),
            data={
                "action": "invite",
                "vorname": "Bettina",
                "nachname": "Beirat",
                "email": "bettina@sc-muster.de",
                "rolle": "admin",
            },
        )
        assert post_response.status_code == 302
        assert post_response.url == reverse("core:onboarding_step_5")
        follow_response = client.get(post_response.url)
        assert follow_response.status_code == 200
        assert StaffInvitation.objects.filter(email="bettina@sc-muster.de").exists()

    def test_mitglied_forbidden_from_step_5(self, client, mitglied_user):
        """Negativtest / Rollenprüfung: Mitglied erhält 403 auf Schritt 5."""
        client.force_login(mitglied_user)
        response = client.get(reverse("core:onboarding_step_5"))
        assert response.status_code == 403

    def test_accept_invitation_view_flow(self, client, admin_user):
        invitation = create_staff_invitation(
            email="webflow@sc-muster.de",
            vorname="Web",
            nachname="Flow",
            rolle=ADMIN_GROUP,
            invited_by=admin_user,
            send_mail=False,
        )

        url = reverse("core:accept_invitation", kwargs={"token": invitation.token})
        get_response = client.get(url)
        assert get_response.status_code == 200
        assert "Web Flow" in get_response.content.decode("utf-8")

        post_response = client.post(
            url,
            data={
                "username": "webflow_user",
                "password": "strongPassword123!",
                "password_confirm": "strongPassword123!",
            },
        )
        assert post_response.status_code == 302
        assert post_response.url == reverse("core:dashboard")

        # User angelegt und authentifiziert
        assert User.objects.filter(username="webflow_user").exists()

    def test_accept_invitation_view_invalid_token(self, client):
        """Negativtest: Ungültiges Token leitet zur Login-Seite um."""
        url = reverse("core:accept_invitation", kwargs={"token": "gibtsnicht12345"})
        response = client.get(url)
        assert response.status_code == 302
        assert response.url == reverse("core:login")
