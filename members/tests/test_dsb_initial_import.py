"""Tests für den DSB-ZPS-Initialimport und Datenübernahme im Onboarding (US2, T015)."""

from unittest.mock import patch
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from core.models import AuditLog, ClubProfile, OnboardingProgress
from core.roles import ADMIN_GROUP, MITGLIED_GROUP
from members.models import Member
from members.services.dsb_sync import DSBNetworkError, import_dsb_initial

User = get_user_model()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username="admin_import", password="password123")
    grp, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    user.groups.add(grp)
    return user


@pytest.fixture
def mitglied_user(db):
    user = User.objects.create_user(username="mitglied_import", password="password123")
    grp, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)
    user.groups.add(grp)
    return user


SAMPLE_DSB_DATA = {
    "vkz": "C0101",
    "stand": "2026-10-01",
    "verein": "SC Musterstadt",
    "mitglieder": [
        {
            "mglnr": 1,
            "nachname": "Mustermann",
            "vorname": "Max",
            "geschlecht": "M",
            "geburtsjahr": 1985,
            "status": "aktiv",
            "dwz": 1850,
            "dwz_index": 45,
            "fide_id": "1234567",
            "pkz": "P001",
        },
        {
            "mglnr": 2,
            "nachname": "Schmidt",
            "vorname": "Anna",
            "geschlecht": "W",
            "geburtsjahr": 1998,
            "status": "aktiv",
            "dwz": 1620,
            "dwz_index": 22,
            "fide_id": "",
            "pkz": "P002",
        },
        {
            "mglnr": 3,
            "nachname": "Fischer",
            "vorname": "Klaus",
            "geschlecht": "M",
            "geburtsjahr": 1955,
            "status": "passiv",
            "dwz": 1400,
            "dwz_index": 12,
            "fide_id": "",
            "pkz": "P003",
        },
    ],
}


@pytest.mark.django_db
class TestDSBInitialImportService:
    """Prüfung des reinen Fachservice import_dsb_initial."""

    @patch("members.services.dsb_sync.fetch_dsb_vereinsliste")
    def test_import_success(self, mock_fetch, admin_user):
        mock_fetch.return_value = (SAMPLE_DSB_DATA, False)

        result = import_dsb_initial(vkz="C0101", user=admin_user)
        assert result.erfolg is True
        assert result.anzahl_neu == 3
        assert result.anzahl_uebersprungen == 0
        assert result.vereinsname == "SC Musterstadt"

        # Prüfe angelegte Mitglieder
        assert Member.objects.count() == 3
        max_m = Member.objects.get(nachname="Mustermann")
        assert max_m.vorname == "Max"
        assert max_m.dwz == 1850
        assert max_m.dwz_index == 45
        assert max_m.fide_id == 1234567
        assert max_m.zps_nummer == "C0101"
        assert max_m.status == "aktiv"
        assert max_m.geburtsdatum is not None
        assert max_m.geburtsdatum.year == 1985

        # AuditLog
        assert AuditLog.objects.filter(aktion__icontains="DSB").exists()

    @patch("members.services.dsb_sync.fetch_dsb_vereinsliste")
    def test_import_duplicates_skipped(self, mock_fetch, admin_user):
        mock_fetch.return_value = (SAMPLE_DSB_DATA, False)

        # Max Mustermann existiert bereits
        Member.objects.create(
            vorname="Max",
            nachname="Mustermann",
            zps_nummer="C0101",
            eintrittsdatum="2020-01-01",
            status="aktiv",
        )

        result = import_dsb_initial(vkz="C0101", user=admin_user)
        assert result.erfolg is True
        assert result.anzahl_neu == 2
        assert result.anzahl_uebersprungen == 1

    @patch("members.services.dsb_sync.fetch_dsb_vereinsliste")
    def test_import_network_error(self, mock_fetch, admin_user):
        mock_fetch.side_effect = DSBNetworkError("Timeout beim DSB-Server")

        result = import_dsb_initial(vkz="C0101", user=admin_user)
        assert result.erfolg is False
        assert len(result.fehler_meldungen) > 0
        assert "Timeout" in result.fehler_meldungen[0]

    def test_import_invalid_vkz(self, admin_user):
        result = import_dsb_initial(vkz="", user=admin_user)
        assert result.erfolg is False
        assert any("Vereinskennziffer" in err for err in result.fehler_meldungen)


@pytest.mark.django_db
class TestOnboardingStep4View:
    """Prüfung der View für Schritt 4 (ZPS-Import und CSV)."""

    def test_step_4_forbidden_for_mitglied(self, client, mitglied_user):
        client.force_login(mitglied_user)
        response = client.get(reverse("core:onboarding_step_4"))
        assert response.status_code == 403

    @patch("members.services.dsb_sync.fetch_dsb_vereinsliste")
    def test_step_4_post_zps_import(self, mock_fetch, client, admin_user):
        mock_fetch.return_value = (SAMPLE_DSB_DATA, False)
        client.force_login(admin_user)

        url = reverse("core:onboarding_step_4")
        response = client.post(url, data={"action": "import_zps", "zps_nummer": "C0101"})
        assert response.status_code == 302
        assert response.url == reverse("core:onboarding_step_5")

        progress = OnboardingProgress.get_solo()
        assert "mitglieder" in progress.schritte_abgeschlossen

    def test_step_4_skip(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("core:onboarding_step_4")
        response = client.post(url, data={"action": "skip"})
        assert response.status_code == 302
        assert response.url == reverse("core:onboarding_step_5")
