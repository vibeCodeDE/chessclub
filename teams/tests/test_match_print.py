"""Tests für die Spielbericht-Druckansicht (Hebel F2 & D3)."""

from datetime import date, time

from django.contrib.auth.models import Group, User
from django.test import TestCase

from members.models import Member
from teams.models import LeagueMatch, LineupEntry, Team


def make_user(username, role="mitglied"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    return user


class MatchPrintViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("admin_user", "admin")
        cls.kapitaen_user = make_user("kapitaen_user", "kapitaen")
        cls.mitglied = make_user("mitglied_user", "mitglied")

        cls.m1 = Member.objects.create(
            user=cls.kapitaen_user,
            vorname="Klaus", nachname="Kapitaen",
            eintrittsdatum=date(2020, 1, 1), dwz=1950, dwz_index=42,
        )
        cls.m2 = Member.objects.create(
            user=cls.mitglied,
            vorname="Moritz", nachname="Mitglied",
            eintrittsdatum=date(2021, 1, 1), dwz=1820, dwz_index=15,
        )

        cls.team = Team.objects.create(
            name="1. Mannschaft", liga="Landesliga Nord",
            brettanzahl=4, kapitaen=cls.m1,
        )
        cls.match = LeagueMatch.objects.create(
            team=cls.team,
            datum=date(2026, 11, 15),
            uhrzeit=time(10, 0),
            gegner="SK Doppelbauer",
            heimspiel=True,
            ort="Bürgerhaus Saal 1",
            runde="Runde 3",
            brettanzahl=4,
            status=LeagueMatch.Status.AUFGESTELLT,
        )

        # Aufstellung
        LineupEntry.objects.create(
            match=cls.match, brett=1, member=cls.m1,
            gegner_name="Dr. Großmeister", ergebnis=LineupEntry.Ergebnis.SIEG,
        )
        LineupEntry.objects.create(
            match=cls.match, brett=2, member=cls.m2,
            gegner_name="Meister Schwarz", ergebnis=LineupEntry.Ergebnis.REMIS,
        )
        LineupEntry.objects.create(
            match=cls.match, brett=3, member=None, ersatz_name="Gastspieler E.",
            gegner_name="Gegner Drei", ergebnis=LineupEntry.Ergebnis.NIEDERLAGE,
        )
        LineupEntry.objects.create(
            match=cls.match, brett=4, member=None,
            gegner_name="", ergebnis=LineupEntry.Ergebnis.OFFEN,
        )

    def test_match_print_admin_erfolg(self):
        self.client.force_login(self.admin)
        url = f"/spiele/{self.match.pk}/drucken/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Offizieller Spielbericht", content)
        self.assertIn("1. Mannschaft", content)
        self.assertIn("SK Doppelbauer", content)
        self.assertIn("Landesliga Nord", content)
        self.assertIn("Kapitaen", content)
        self.assertIn("1950", content)
        self.assertIn("Dr. Großmeister", content)
        self.assertIn("Unterschrift", content)

    def test_match_print_kapitaen_erfolg(self):
        self.client.force_login(self.kapitaen_user)
        url = f"/spiele/{self.match.pk}/drucken/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_match_print_mitglied_negativtest_403(self):
        # Nach PRD §3.8: Rolle mitglied hat keinen Zugriff auf die Spielbetriebs-Verwaltung (403)
        self.client.force_login(self.mitglied)
        url = f"/spiele/{self.match.pk}/drucken/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_match_print_gast_redirects_login(self):
        url = f"/spiele/{self.match.pk}/drucken/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_match_print_404_fuer_unbekanntes_spiel(self):
        self.client.force_login(self.admin)
        response = self.client.get("/spiele/99999/drucken/")
        self.assertEqual(response.status_code, 404)
