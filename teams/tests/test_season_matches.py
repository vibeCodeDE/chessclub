"""Tests für saisonbezogenen Spielbetrieb und Datumsvalidierung (PRD US2)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, MITGLIED_GROUP
from teams.models import LeagueMatch, Season, Team
from teams.services import validate_match_season_bounds

User = get_user_model()


class SeasonMatchValidationTests(TestCase):
    """Prüft die Datumsvalidierung von Ligaspielen bezüglich des Saisonfensters."""

    def setUp(self):
        self.saison_25_26, _ = Season.objects.get_or_create(
            name="2025/2026",
            defaults={
                "startdatum": date(2025, 8, 1),
                "enddatum": date(2026, 7, 31),
                "ist_aktiv": False,
            },
        )
        self.saison_25_26.ist_aktiv = False
        self.saison_25_26.save()
        self.saison_26_27, _ = Season.objects.get_or_create(
            name="2026/2027",
            defaults={
                "startdatum": date(2026, 8, 1),
                "enddatum": date(2027, 7, 31),
                "ist_aktiv": True,
            },
        )
        self.saison_26_27.ist_aktiv = True
        self.saison_26_27.save()
        self.team_neu = Team.objects.create(
            name="1. Mannschaft",
            saison=self.saison_26_27,
            liga="Verbandsliga",
            brettanzahl=8,
        )

    def test_gueltiges_spieldatum_innerhalb_der_saison_besteht_validierung(self):
        match = LeagueMatch(
            team=self.team_neu,
            datum=date(2026, 10, 15),
            gegner="SV Turm",
            brettanzahl=8,
        )
        # Sollte fehlerfrei durchlaufen
        validate_match_season_bounds(match)
        match.full_clean()

    def test_negativtest_spieldatum_vor_saisonstart_wirft_validation_error(self):
        match = LeagueMatch(
            team=self.team_neu,
            datum=date(2026, 7, 15),  # 17 Tage vor Saisonbeginn am 01.08.2026
            gegner="SV Turm",
            brettanzahl=8,
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_match_season_bounds(match)
        self.assertIn("datum", ctx.exception.message_dict)

        with self.assertRaises(ValidationError) as ctx:
            match.full_clean()
        self.assertIn("datum", ctx.exception.message_dict)

    def test_negativtest_spieldatum_nach_saisonende_wirft_validation_error(self):
        match = LeagueMatch(
            team=self.team_neu,
            datum=date(2027, 8, 5),  # Nach Saisonende am 31.07.2027
            gegner="SV Turm",
            brettanzahl=8,
        )
        with self.assertRaises(ValidationError) as ctx:
            validate_match_season_bounds(match)
        self.assertIn("datum", ctx.exception.message_dict)


class SeasonMatchViewFilterTests(TestCase):
    """Prüft die Filterung von Mannschaften und Spielen nach Saison in Views."""

    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        kapitaen_group, _ = Group.objects.get_or_create(name=KAPITAEN_GROUP)
        mitglied_group, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)

        self.admin = User.objects.create_user(username="admin_user", password="password123")
        self.admin.groups.add(admin_group)

        self.mitglied_user = User.objects.create_user(username="mitglied_user", password="password123")
        self.mitglied_user.groups.add(mitglied_group)

        from core.models import ClubProfile, ModuleSettings
        from teams.models import LeagueCalendarFeed
        ClubProfile.get_solo()
        ModuleSettings.get_solo()
        LeagueCalendarFeed.objects.get_or_create(name="gesamt")

        self.saison_alt, _ = Season.objects.get_or_create(
            name="2024/2025",
            defaults={
                "startdatum": date(2024, 8, 1),
                "enddatum": date(2025, 7, 31),
                "status": Season.Status.ARCHIVIERT,
                "ist_aktiv": False,
            },
        )
        self.saison_aktuell, _ = Season.objects.get_or_create(
            name="2025/2026",
            defaults={
                "startdatum": date(2025, 8, 1),
                "enddatum": date(2026, 7, 31),
                "status": Season.Status.AKTIV,
                "ist_aktiv": True,
            },
        )
        self.saison_aktuell.status = Season.Status.AKTIV
        self.saison_aktuell.ist_aktiv = True
        self.saison_aktuell.save()

        self.team_alt = Team.objects.create(
            name="Historisches Team",
            saison=self.saison_alt,
            liga="Bezirksliga",
            brettanzahl=8,
        )
        self.team_aktuell = Team.objects.create(
            name="Aktuelles Team",
            saison=self.saison_aktuell,
            liga="Landesliga",
            brettanzahl=8,
        )

        self.match_alt = LeagueMatch.objects.create(
            team=self.team_alt,
            datum=date(2024, 11, 10),
            gegner="SV Altstadt",
            brettanzahl=8,
        )
        self.match_aktuell = LeagueMatch.objects.create(
            team=self.team_aktuell,
            datum=date(2025, 11, 10),
            gegner="SV Neustadt",
            brettanzahl=8,
        )

    def test_team_list_filtert_standardmaessig_auf_aktive_saison(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("teams:team_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aktuelles Team")
        self.assertNotContains(response, "Historisches Team")

    def test_team_list_filtert_nach_historischer_saison(self):
        self.client.force_login(self.admin)
        response = self.client.get(f"{reverse('teams:team_list')}?saison={self.saison_alt.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historisches Team")
        self.assertNotContains(response, "Aktuelles Team")

    def test_match_list_filtert_standardmaessig_auf_aktive_saison(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("teams:match_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SV Neustadt")
        self.assertNotContains(response, "SV Altstadt")

    def test_match_list_filtert_nach_historischer_saison(self):
        self.client.force_login(self.admin)
        response = self.client.get(f"{reverse('teams:match_list')}?saison={self.saison_alt.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SV Altstadt")
        self.assertNotContains(response, "SV Neustadt")

    def test_negativtest_nicht_team_rolle_erhaelt_403(self):
        self.client.force_login(self.mitglied_user)
        response = self.client.get(reverse("teams:team_list"))
        self.assertEqual(response.status_code, 403)

        response_match = self.client.get(reverse("teams:match_list"))
        self.assertEqual(response_match.status_code, 403)

    def test_team_list_query_budget_ohne_n_plus_1(self):
        self.client.force_login(self.admin)
        with self.assertNumQueries(23):  # Feste Obergrenze ohne N+1 (Global-Context + Prefetch)
            response = self.client.get(reverse("teams:team_list"))
            self.assertEqual(response.status_code, 200)

    def test_match_list_query_budget_ohne_n_plus_1(self):
        self.client.force_login(self.admin)
        with self.assertNumQueries(19):  # Feste Obergrenze ohne N+1 (Global-Context + Paginator + Prefetch)
            response = self.client.get(reverse("teams:match_list"))
            self.assertEqual(response.status_code, 200)
