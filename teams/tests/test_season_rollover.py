"""Tests für den geführten Saisonwechsel & Mannschaftsübernahme (Rollover, US3)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, MITGLIED_GROUP
from members.models import Member
from teams.models import LeagueMatch, Season, Team
from teams.services import rollover_teams

User = get_user_model()


class SeasonRolloverServiceTests(TestCase):
    """Testet die reine Logik des Mannschafts-Rollovers in teams/services.py."""

    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        self.admin = User.objects.create_user(username="admin_rollover", password="password123")
        self.admin.groups.add(admin_group)

        self.kapitaen_member = Member.objects.create(
            vorname="Max",
            nachname="Mustermann",
            email="max@schachverein.de",
            eintrittsdatum=date(2020, 1, 1),
            status=Member.Status.AKTIV,
        )

        self.saison_alt, _ = Season.objects.get_or_create(
            name="2025/2026",
            defaults={
                "startdatum": date(2025, 8, 1),
                "enddatum": date(2026, 7, 31),
                "ist_aktiv": False,
            },
        )
        self.saison_neu, _ = Season.objects.get_or_create(
            name="2026/2027",
            defaults={
                "startdatum": date(2026, 8, 1),
                "enddatum": date(2027, 7, 31),
                "ist_aktiv": True,
            },
        )

        self.team1 = Team.objects.create(
            name="1. Mannschaft",
            saison=self.saison_alt,
            liga="Verbandsliga",
            brettanzahl=8,
            kapitaen=self.kapitaen_member,
            aktiv=True,
        )
        self.team2 = Team.objects.create(
            name="2. Mannschaft",
            saison=self.saison_alt,
            liga="Bezirksliga",
            brettanzahl=6,
            aktiv=True,
        )

        self.match_team1 = LeagueMatch.objects.create(
            team=self.team1,
            datum=date(2025, 10, 12),
            gegner="SF Berlin",
            brettanzahl=8,
        )

    def test_rollover_teams_erzeugt_neue_teams_mit_frischem_token_und_leerem_spielplan(self):
        payload = [
            {
                "source_team_id": self.team1.pk,
                "uebernehmen": True,
                "liga": "Oberliga",  # Aufstieg!
                "brettanzahl": 8,
                "kapitaen_id": self.kapitaen_member.pk,
            },
            {
                "source_team_id": self.team2.pk,
                "uebernehmen": False,  # Abgewählt
            },
        ]

        created = rollover_teams(
            source_season=self.saison_alt,
            target_season=self.saison_neu,
            teams_payload=payload,
            user=self.admin,
        )

        self.assertEqual(len(created), 1)
        new_team = created[0]

        # Neues Team in Zielsaison mit neuen Parametern
        self.assertEqual(new_team.saison, self.saison_neu)
        self.assertEqual(new_team.name, "1. Mannschaft")
        self.assertEqual(new_team.liga, "Oberliga")
        self.assertEqual(new_team.kapitaen, self.kapitaen_member)
        self.assertNotEqual(new_team.ical_token, self.team1.ical_token)
        self.assertEqual(new_team.matches.count(), 0)  # Frischer Spielplan!

        # Altes Team unverändert in Altsaison erhalten
        self.team1.refresh_from_db()
        self.assertEqual(self.team1.saison, self.saison_alt)
        self.assertEqual(self.team1.liga, "Verbandsliga")
        self.assertEqual(self.team1.matches.count(), 1)

        # AuditLog geprüft
        log_eintrag = AuditLog.objects.filter(aktion="Mannschaftsübernahme").latest("zeitpunkt")
        self.assertIn("2025/2026 nach 2026/2027", log_eintrag.text)
        self.assertEqual(log_eintrag.benutzer, self.admin)


class SeasonRolloverViewTests(TestCase):
    """Testet die View season_rollover inklusive Rollenberechtigungen."""

    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        kapitaen_group, _ = Group.objects.get_or_create(name=KAPITAEN_GROUP)
        mitglied_group, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)

        self.admin = User.objects.create_user(username="admin_view", password="password123")
        self.admin.groups.add(admin_group)

        self.kapitaen = User.objects.create_user(username="kapitaen_view", password="password123")
        self.kapitaen.groups.add(kapitaen_group)

        self.mitglied = User.objects.create_user(username="mitglied_view", password="password123")
        self.mitglied.groups.add(mitglied_group)

        self.saison_alt, _ = Season.objects.get_or_create(
            name="2025/2026",
            defaults={
                "startdatum": date(2025, 8, 1),
                "enddatum": date(2026, 7, 31),
                "ist_aktiv": False,
            },
        )
        self.saison_neu, _ = Season.objects.get_or_create(
            name="2026/2027",
            defaults={
                "startdatum": date(2026, 8, 1),
                "enddatum": date(2027, 7, 31),
                "ist_aktiv": True,
            },
        )
        self.team_alt = Team.objects.create(
            name="1. Mannschaft",
            saison=self.saison_alt,
            liga="Verbandsliga",
            brettanzahl=8,
            aktiv=True,
        )

    def test_admin_kann_rollover_maske_aufrufen(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("teams:season_rollover", kwargs={"pk": self.saison_neu.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mannschaftsübernahme")
        self.assertContains(response, "1. Mannschaft")

    def test_admin_kann_rollover_durchfuehren_und_wird_weitergeleitet(self):
        self.client.force_login(self.admin)
        post_data = {
            "source_season_id": self.saison_alt.pk,
            f"team_{self.team_alt.pk}_uebernehmen": "1",
            f"team_{self.team_alt.pk}_liga": "Oberliga Süd",
            f"team_{self.team_alt.pk}_brettanzahl": "8",
        }
        response = self.client.post(
            reverse("teams:season_rollover", kwargs={"pk": self.saison_neu.pk}),
            data=post_data,
        )
        self.assertRedirects(response, f"{reverse('teams:team_list')}?saison={self.saison_neu.pk}")

        # Team existiert nun in 2026/2027
        new_team = Team.objects.filter(saison=self.saison_neu, name="1. Mannschaft").first()
        self.assertIsNotNone(new_team)
        self.assertEqual(new_team.liga, "Oberliga Süd")

    def test_negativ_kapitaen_und_mitglied_erhalten_403(self):
        self.client.force_login(self.kapitaen)
        res_kap = self.client.get(reverse("teams:season_rollover", kwargs={"pk": self.saison_neu.pk}))
        self.assertEqual(res_kap.status_code, 403)

        self.client.force_login(self.mitglied)
        res_mit = self.client.post(
            reverse("teams:season_rollover", kwargs={"pk": self.saison_neu.pk}),
            data={"source_season_id": self.saison_alt.pk},
        )
        self.assertEqual(res_mit.status_code, 403)
