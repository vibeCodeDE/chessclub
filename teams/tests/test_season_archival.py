"""Tests für Saisonabschluss, Schreibschutz und Revisionssicherheit (US5)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, MITGLIED_GROUP
from members.models import Member
from teams.models import LeagueMatch, LineupEntry, Season, Team
from teams.services import (
    archive_season,
    check_match_edit_allowed,
    delete_season,
    reopen_season,
)

User = get_user_model()


class SeasonArchivalServiceTests(TestCase):
    """Testet Archivierung, Warnungen, Entsperrung und Löschsperre in teams/services.py."""

    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        self.admin = User.objects.create_user(username="admin_archival", password="password123")
        self.admin.groups.add(admin_group)

        self.saison = Season.objects.create(
            name="2023/2024",
            startdatum=date(2023, 8, 1),
            enddatum=date(2024, 7, 31),
            status=Season.Status.AKTIV,
            ist_aktiv=True,
        )
        self.team = Team.objects.create(
            name="Archiv-Team",
            saison=self.saison,
            liga="Bezirksklasse",
            brettanzahl=8,
        )

    def test_archivierung_warnt_bei_ungespielten_begegnungen(self):
        match_offen = LeagueMatch.objects.create(
            team=self.team,
            datum=date(2024, 3, 10),
            gegner="SF Offen",
            status=LeagueMatch.Status.GEPLANT,
        )

        # Ohne force=True schlägt Archivierung fehl und gibt Warnung zurück
        erfolg, warnungen = archive_season(self.saison, force=False, user=self.admin)
        self.assertFalse(erfolg)
        self.assertEqual(len(warnungen), 1)
        self.assertIn("SF Offen", warnungen[0])

        self.saison.refresh_from_db()
        self.assertEqual(self.saison.status, Season.Status.AKTIV)

        # Mit force=True wird trotzdem archiviert
        erfolg_force, _ = archive_season(self.saison, force=True, user=self.admin)
        self.assertTrue(erfolg_force)
        self.saison.refresh_from_db()
        self.assertEqual(self.saison.status, Season.Status.ARCHIVIERT)
        self.assertFalse(self.saison.ist_aktiv)

    def test_reaktivierung_stellt_aktiven_status_wieder_her(self):
        self.saison.status = Season.Status.ARCHIVIERT
        self.saison.save()

        reopen_season(self.saison, user=self.admin)
        self.saison.refresh_from_db()
        self.assertEqual(self.saison.status, Season.Status.AKTIV)

        log = AuditLog.objects.filter(aktion="Saison reaktiviert").latest("zeitpunkt")
        self.assertIn(self.saison.name, log.text)

    def test_negativ_loeschsperre_bei_vorhandenen_teams(self):
        with self.assertRaises(ValidationError) as ctx:
            delete_season(self.saison, user=self.admin)
        self.assertIn("Mannschaften", str(ctx.exception))

    def test_leere_saison_kann_geloescht_werden(self):
        leere_saison = Season.objects.create(
            name="2029/2030",
            startdatum=date(2029, 8, 1),
            enddatum=date(2030, 7, 31),
        )
        pk = leere_saison.pk
        delete_season(leere_saison, user=self.admin)
        self.assertFalse(Season.objects.filter(pk=pk).exists())
        log = AuditLog.objects.filter(aktion="Saison gelöscht").latest("zeitpunkt")
        self.assertIn("2029/2030", log.alt_wert)


class SeasonSchreibschutzTests(TestCase):
    """Testet den Schreibschutz auf Begegnungen und Aufstellungen in archivierten Saisons."""

    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        kapitaen_group, _ = Group.objects.get_or_create(name=KAPITAEN_GROUP)
        mitglied_group, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)

        self.admin = User.objects.create_user(username="admin_schreib", password="password123")
        self.admin.groups.add(admin_group)

        self.kapitaen = User.objects.create_user(username="kapitaen_schreib", password="password123")
        self.kapitaen.groups.add(kapitaen_group)

        self.mitglied_user = User.objects.create_user(username="mitglied_schreib", password="password123")
        self.mitglied_user.groups.add(mitglied_group)

        self.kapitaen_member = Member.objects.create(
            user=self.kapitaen,
            vorname="Karl",
            nachname="Kapitän",
            email="karl@schach.de",
            eintrittsdatum=date(2020, 1, 1),
            status=Member.Status.AKTIV,
        )

        self.saison_archiv = Season.objects.create(
            name="2022/2023",
            startdatum=date(2022, 8, 1),
            enddatum=date(2023, 7, 31),
            status=Season.Status.ARCHIVIERT,
            ist_aktiv=False,
        )
        self.team = Team.objects.create(
            name="Historisches Team",
            saison=self.saison_archiv,
            liga="Verbandsliga",
            brettanzahl=8,
            kapitaen=self.kapitaen_member,
            aktiv=True,
        )
        self.match = LeagueMatch.objects.create(
            team=self.team,
            datum=date(2022, 10, 20),
            gegner="Alte SF",
            status=LeagueMatch.Status.GESPIELT,
            brettanzahl=8,
        )

    def test_check_match_edit_allowed_wirft_permission_denied_bei_archivierter_saison(self):
        with self.assertRaises(PermissionDenied):
            check_match_edit_allowed(self.match)

    def test_negativ_bearbeiten_des_spiels_in_archivierter_saison_wird_abgewehrt(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("teams:match_update", kwargs={"pk": self.match.pk}))
        self.assertEqual(response.status_code, 403)

        response_post = self.client.post(
            reverse("teams:match_update", kwargs={"pk": self.match.pk}),
            data={"datum": "2022-10-21"},
        )
        self.assertEqual(response_post.status_code, 403)

    def test_negativ_loeschen_des_spiels_in_archivierter_saison_wird_abgewehrt(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("teams:match_delete", kwargs={"pk": self.match.pk}))
        self.assertEqual(response.status_code, 403)

    def test_negativ_lineup_save_in_archivierter_saison_wird_abgewehrt(self):
        self.client.force_login(self.kapitaen)
        response = self.client.post(
            reverse("teams:lineup_board_save", kwargs={"pk": self.match.pk, "brett": 1}),
            data={"gegner_name": "Testgegner"},
        )
        self.assertEqual(response.status_code, 403)

        response_full = self.client.post(
            reverse("teams:lineup_save", kwargs={"pk": self.match.pk}),
            data={"member_1": ""},
        )
        self.assertEqual(response_full.status_code, 403)

    def test_match_detail_zeigt_archiv_banner_und_deaktiviert_aufstellungsfelder(self):
        self.client.force_login(self.kapitaen)
        response = self.client.get(reverse("teams:match_detail", kwargs={"pk": self.match.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Archivierte Spielzeit")
        self.assertContains(response, "Alle Aufstellungen und Ergebnisse sind schreibgeschützt")
        self.assertFalse(response.context["darf_aufstellen"])

    def test_negativ_nicht_admin_kann_saison_nicht_archivieren_oder_loeschen(self):
        self.client.force_login(self.kapitaen)
        res_arch = self.client.post(reverse("teams:season_archive", kwargs={"pk": self.saison_archiv.pk}))
        self.assertEqual(res_arch.status_code, 403)

        res_del = self.client.post(reverse("teams:season_delete", kwargs={"pk": self.saison_archiv.pk}))
        self.assertEqual(res_del.status_code, 403)
