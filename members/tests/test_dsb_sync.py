"""Tests für DSB- / DWZ-Synchronisation und Drift Detection (ADR-016 / K3.6)."""

import json
import urllib.error
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TestCase, override_settings

from core.models import AuditLog
from members.models import Member
from members.services.dsb_sync import (
    DSBConfigError,
    DSBNetworkError,
    DSBParseError,
    detect_drift,
    fetch_dsb_vereinsliste,
    parse_dsb_data,
    sync_dwz_from_report,
)


def make_user(username, group_name=None):
    user = User.objects.create_user(username, password="x")
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


def make_member(vorname, nachname, **kwargs):
    defaults = {"eintrittsdatum": date(2025, 1, 1), "status": Member.Status.AKTIV}
    defaults.update(kwargs)
    return Member.objects.create(vorname=vorname, nachname=nachname, **defaults)


SAMPLE_DSB_PAYLOAD = {
    "stand": "2026-10-07T12:00:00",
    "vkz": "C0101",
    "verein": "SF Essen-Werden",
    "spieler": [
        {
            "id": "1001",
            "nachname": "Mustermann",
            "vorname": "Max",
            "dwz": 1850,
            "dwzIndex": 45,
            "fideId": 1234567,
            "status": "A",
            "zps": "C0101-001",
            "mitgliedsnummer": "001",
            "geburtsjahr": "1990",
            "nation": "GER",
        },
        {
            "id": "1002",
            "nachname": "Schmidt",
            "vorname": "Sara",
            "dwz": 1620,
            "dwzIndex": 22,
            "status": "P",  # Passiv
            "zps": "C0101-002",
            "mitgliedsnummer": "002",
            "geburtsjahr": "1995",
            "nation": "GER",
        },
        {
            "id": "1003",
            "nachname": "Neumann",
            "vorname": "Nico",
            "dwz": 2100,
            "dwzIndex": 60,
            "status": "A",
            "zps": "C0101-003",
            "mitgliedsnummer": "003",
            "geburtsjahr": "2000",
            "nation": "GER",
        },
    ],
}


class DSBServiceFetchAndCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @override_settings(DSB_VKZ="", DSB_API_TOKEN="")
    def test_missing_config_raises_dsb_config_error(self):
        """Negativtest: Fehlende Konfiguration führt zu klarem DSBConfigError."""
        with self.assertRaises(DSBConfigError):
            fetch_dsb_vereinsliste()

    @override_settings(DSB_VKZ="C0101", DSB_API_TOKEN="secret-token")
    @patch("urllib.request.urlopen")
    def test_fetch_and_caching(self, mock_urlopen):
        """Erster Abruf holt Daten von der Schnittstelle; zweiter Abruf nutzt den Cache."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(SAMPLE_DSB_PAYLOAD).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # 1. Abruf -> Netzwerk
        data, from_cache = fetch_dsb_vereinsliste()
        self.assertFalse(from_cache)
        self.assertEqual(data["vkz"], "C0101")
        self.assertEqual(len(data["spieler"]), 3)
        self.assertEqual(mock_urlopen.call_count, 1)

        # 2. Abruf -> aus Cache, kein zweiter Netzwerk-Aufruf
        data_cached, from_cache_2 = fetch_dsb_vereinsliste()
        self.assertTrue(from_cache_2)
        self.assertEqual(data_cached["vkz"], "C0101")
        self.assertEqual(mock_urlopen.call_count, 1)

        # 3. Abruf mit force=True -> erzwingt neuen Netzwerkabruf
        data_forced, from_cache_forced = fetch_dsb_vereinsliste(force=True)
        self.assertFalse(from_cache_forced)
        self.assertEqual(mock_urlopen.call_count, 2)

    @override_settings(DSB_VKZ="C0101", DSB_API_TOKEN="secret-token")
    @patch("urllib.request.urlopen")
    def test_network_http_error_handled(self, mock_urlopen):
        """Negativtest: HTTP-Fehler beim Verbandsserver wird als DSBNetworkError geworfen."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.org", code=503, msg="Service Unavailable", hdrs={}, fp=BytesIO()
        )
        with self.assertRaises(DSBNetworkError):
            fetch_dsb_vereinsliste()

    def test_invalid_json_raises_parse_error(self):
        """Negativtest: Korrupte JSON-Antwort löst DSBParseError aus."""
        with self.assertRaises(DSBParseError):
            parse_dsb_data("kein json content")


class DriftDetectionTests(TestCase):
    def test_drift_detection_scenarios(self):
        # 1. Max: Hat veraltete DWZ (1800 statt 1850) -> dwz_abweichung
        max_m = make_member("Max", "Mustermann", pkz="1001", dwz=1800, dwz_index=44)

        # 2. Sara: Im Verein aktiv, beim Verband passiv ("P") -> status_abweichung
        sara_m = make_member(
            "Sara", "Schmidt", pkz="1002", dwz=1620, dwz_index=22, status=Member.Status.AKTIV
        )

        # 3. Lukas: Im Verein aktiv, fehlt in der Verbandsliste -> fehlt_im_verband
        lukas_m = make_member("Lukas", "Lokal")

        # Verbandsdaten parsen (enthält Mustermann, Schmidt, und Nico Neumann)
        parsed_dsb = parse_dsb_data(SAMPLE_DSB_PAYLOAD)

        report = detect_drift(members_qs=Member.objects.all(), dsb_data=parsed_dsb)

        # Prüfungen
        self.assertEqual(report.total_verband, 3)
        self.assertEqual(report.total_verein, 3)

        # DWZ-Abweichung für Max
        self.assertEqual(len(report.dwz_abweichungen), 1)
        self.assertEqual(report.dwz_abweichungen[0]["member"], max_m)
        self.assertEqual(report.dwz_abweichungen[0]["dwz_alt"], 1800)
        self.assertEqual(report.dwz_abweichungen[0]["dwz_neu"], 1850)
        self.assertEqual(report.dwz_abweichungen[0]["index_neu"], 45)

        # Status-Abweichung für Sara (Verein aktiv, Verband passiv)
        self.assertEqual(len(report.status_abweichungen), 1)
        self.assertEqual(report.status_abweichungen[0]["member"], sara_m)

        # Fehlt im Verband: Lukas
        self.assertEqual(len(report.fehlt_im_verband), 1)
        self.assertEqual(report.fehlt_im_verband[0], lukas_m)

        # Fehlt im Verein: Nico Neumann
        self.assertEqual(len(report.fehlt_im_verein), 1)
        self.assertEqual(report.fehlt_im_verein[0]["nachname"], "Neumann")

    def test_matching_by_name_and_zps(self):
        """Prüft, dass Spieler auch ohne PKZ per ZPS-Nummer oder Namen gematcht werden."""
        member_name_match = make_member("Max", "Mustermann", dwz=1850, dwz_index=45)
        parsed_dsb = parse_dsb_data(
            {
                "spieler": [
                    {
                        "nachname": "Mustermann",
                        "vorname": "Max",
                        "dwz": 1850,
                        "dwzIndex": 45,
                        "status": "A",
                    }
                ]
            }
        )
        report = detect_drift(members_qs=Member.objects.all(), dsb_data=parsed_dsb)
        self.assertEqual(len(report.synchrone_mitglieder), 1)
        self.assertEqual(report.synchrone_mitglieder[0]["member"], member_name_match)

    def test_detect_drift_query_budget(self):
        """Regel: Keine N+1-Abfragen beim Abgleich."""
        for i in range(10):
            make_member(f"Vorname{i}", f"Nachname{i}", dwz=1500, dwz_index=10)

        parsed_dsb = parse_dsb_data(
            {
                "spieler": [
                    {
                        "nachname": f"Nachname{i}",
                        "vorname": f"Vorname{i}",
                        "dwz": 1550,
                        "dwzIndex": 11,
                        "status": "A",
                    }
                    for i in range(10)
                ]
            }
        )
        # Exakt 1 Query für alle Mitglieder, reiner In-Memory-Vergleich
        with self.assertNumQueries(1):
            detect_drift(members_qs=Member.objects.all(), dsb_data=parsed_dsb)


class SyncDWZTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin_user", "admin")

    def test_sync_dwz_from_report_and_audit_log(self):
        member = make_member("Max", "Mustermann", pkz="1001", dwz=1750, dwz_index=40)
        parsed_dsb = parse_dsb_data(SAMPLE_DSB_PAYLOAD)
        report = detect_drift(members_qs=Member.objects.all(), dsb_data=parsed_dsb)

        AuditLog.objects.all().delete()
        updated_count = sync_dwz_from_report(report, benutzer=self.admin)

        self.assertEqual(updated_count, 1)
        member.refresh_from_db()
        self.assertEqual(member.dwz, 1850)
        self.assertEqual(member.dwz_index, 45)
        self.assertEqual(member.fide_id, 1234567)
        self.assertEqual(member.zps_nummer, "C0101-001")
        self.assertEqual(member.dwz_formatiert, "1850-45")

        # Audit-Log Eintrag für Gesamt-Aktion
        overall_audit = AuditLog.objects.filter(aktion="DSB-Abgleich durchgeführt").first()
        self.assertIsNotNone(overall_audit)
        self.assertEqual(overall_audit.benutzer, self.admin)

        # Audit-Log Signal-Einträge für Feld-Änderungen an Mitglied
        dwz_change_audit = AuditLog.objects.filter(
            aktion="Stammdaten geändert", feld="dwz", member=member
        ).first()
        self.assertIsNotNone(dwz_change_audit)
        self.assertEqual(dwz_change_audit.alt_wert, "1750")
        self.assertEqual(dwz_change_audit.neu_wert, "1850")

    def test_sync_dwz_idempotent(self):
        """Zweiter Sync-Lauf ohne Änderungen führt zu 0 Updates."""
        make_member("Max", "Mustermann", pkz="1001", dwz=1850, dwz_index=45)
        parsed_dsb = parse_dsb_data(SAMPLE_DSB_PAYLOAD)
        report = detect_drift(members_qs=Member.objects.all(), dsb_data=parsed_dsb)

        updated_count = sync_dwz_from_report(report, benutzer=self.admin)
        self.assertEqual(updated_count, 0)


class DSBSyncViewAndPermissionsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user("admin_user", "admin")
        self.kapitaen = make_user("kapitaen_user", "kapitaen")
        self.mitglied = make_user("mitglied_user", "mitglied")
        self.member = make_member("Max", "Mustermann", pkz="1001", dwz=1750, dwz_index=40)

    def tearDown(self):
        cache.clear()

    def test_anonymous_redirected_to_login(self):
        response = self.client.get("/mitglieder/dsb-sync/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_mitglied_role_forbidden(self):
        """Negativtest (Berechtigungsmatrix §3.8): Rolle 'mitglied' erhält 403."""
        self.client.force_login(self.mitglied)
        response = self.client.get("/mitglieder/dsb-sync/")
        self.assertEqual(response.status_code, 403)

    def test_kapitaen_role_forbidden(self):
        """Negativtest (Berechtigungsmatrix §3.8): Rolle 'kapitaen' erhält 403."""
        self.client.force_login(self.kapitaen)
        response = self.client.get("/mitglieder/dsb-sync/")
        self.assertEqual(response.status_code, 403)

    @override_settings(DSB_VKZ="C0101", DSB_API_TOKEN="valid-token")
    @patch("members.services.dsb_sync.fetch_dsb_vereinsliste")
    def test_admin_can_view_dsb_sync_page(self, mock_fetch):
        mock_fetch.return_value = (parse_dsb_data(SAMPLE_DSB_PAYLOAD), True)
        self.client.force_login(self.admin)

        response = self.client.get("/mitglieder/dsb-sync/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "members/dsb_sync.html")
        self.assertContains(response, "DSB- / DWZ-Synchronisation")
        self.assertContains(response, "Mustermann")
        self.assertContains(response, "1850-45")

    @override_settings(DSB_VKZ="C0101", DSB_API_TOKEN="valid-token")
    @patch("members.services.dsb_sync.fetch_dsb_vereinsliste")
    def test_admin_post_sync_all(self, mock_fetch):
        mock_fetch.return_value = (parse_dsb_data(SAMPLE_DSB_PAYLOAD), False)
        self.client.force_login(self.admin)

        response = self.client.post("/mitglieder/dsb-sync/", {"action": "sync_all"})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/mitglieder/dsb-sync/")

        self.member.refresh_from_db()
        self.assertEqual(self.member.dwz, 1850)
        self.assertEqual(self.member.dwz_index, 45)

    @override_settings(DSB_VKZ="C0101", DSB_API_TOKEN="valid-token")
    @patch("members.services.dsb_sync.fetch_dsb_vereinsliste")
    def test_admin_post_sync_single_member(self, mock_fetch):
        mock_fetch.return_value = (parse_dsb_data(SAMPLE_DSB_PAYLOAD), False)
        self.client.force_login(self.admin)

        response = self.client.post(
            "/mitglieder/dsb-sync/",
            {"action": "sync_member", "member_id": str(self.member.pk)},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/mitglieder/dsb-sync/")

        self.member.refresh_from_db()
        self.assertEqual(self.member.dwz, 1850)

    @override_settings(DSB_VKZ="", DSB_API_TOKEN="")
    def test_post_without_config_shows_error(self):
        """Negativtest: POST ohne Konfiguration bricht ab."""
        self.client.force_login(self.admin)
        response = self.client.post("/mitglieder/dsb-sync/", {"action": "refresh"})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/mitglieder/dsb-sync/")
