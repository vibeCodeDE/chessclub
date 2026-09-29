"""Aufstellung, automatische Brettsumme, Tabellenberechnung und Berechtigungen."""

import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from members.models import Member
from teams.models import LeagueMatch, LineupEntry, Team
from teams.services import tabelle


def make_user(username, gruppe):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name=gruppe)
    user.groups.add(group)
    return user


def make_member(vorname, nachname, user=None):
    return Member.objects.create(
        vorname=vorname, nachname=nachname, eintrittsdatum=date(2015, 1, 1), user=user
    )


class AufstellungsTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.kapitaen_user = make_user("k1", "kapitaen")
        self.kapitaen = make_member("Karla", "Kapitän", user=self.kapitaen_user)
        self.spieler = [make_member("Anna", "Meier"), make_member("Bodo", "Bauer"), make_member("Cem", "Cakir")]
        self.mitglied_user = make_user("p1", "mitglied")
        self.mitglied = make_member("Dana", "Dorn", user=self.mitglied_user)
        self.team = Team.objects.create(
            name="1. Mannschaft", liga="Bezirksliga", brettanzahl=4, kapitaen=self.kapitaen
        )
        self.match = LeagueMatch.objects.create(
            team=self.team, datum=date(2026, 10, 10), gegner="SV Test", brettanzahl=4
        )
        self.client.force_login(self.admin)

    def test_brett_autosave_summiert_brettpunkte(self):
        response = self.client.post(
            f"/spiele/{self.match.pk}/brett/1/",
            {"member": self.spieler[0].pk, "gegner_name": "Gegner", "ergebnis": "1"},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"]["[data-brettpunkte]"], "1.0 : 0.0")
        self.assertEqual(daten["patch"]["[data-mannschaftspunkte]"], "Sieg")

        self.client.post(
            f"/spiele/{self.match.pk}/brett/2/",
            {"member": self.spieler[1].pk, "gegner_name": "", "ergebnis": "0"},
            HTTP_ACCEPT="application/json",
        )
        self.match.refresh_from_db()
        self.assertEqual(self.match.brettpunkte, (Decimal("1.0"), Decimal("1.0")))
        self.assertEqual(self.match.mannschaftspunkte, 1)
        self.assertEqual(self.match.status, LeagueMatch.Status.AUFGESTELLT)

    def test_leeres_brett_wird_entfernt(self):
        LineupEntry.objects.create(match=self.match, brett=1, member=self.spieler[0])
        self.client.post(
            f"/spiele/{self.match.pk}/brett/1/", {"member": "", "ergebnis": ""},
            HTTP_ACCEPT="application/json",
        )
        self.assertFalse(LineupEntry.objects.filter(match=self.match, brett=1).exists())

    def test_kapitaen_darf_aufstellen_mitglied_nicht(self):
        self.client.force_login(self.kapitaen_user)
        response = self.client.post(
            f"/spiele/{self.match.pk}/brett/1/",
            {"member": self.spieler[0].pk, "ergebnis": "1"},
            HTTP_ACCEPT="application/json",
        )
        self.assertTrue(json.loads(response.content)["ok"])

        self.client.force_login(self.mitglied_user)
        response = self.client.post(
            f"/spiele/{self.match.pk}/brett/2/",
            {"member": self.spieler[1].pk, "ergebnis": "1"},
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LineupEntry.objects.filter(match=self.match, brett=2).exists())

    def test_formular_fallback_speichert_komplette_aufstellung(self):
        daten = {"csrfmiddlewaretoken": "x"}
        for brett in range(1, 5):
            daten[f"member_{brett}"] = self.spieler[(brett - 1) % 3].pk if brett <= 3 else ""
            daten[f"gegner_{brett}"] = f"Gegner {brett}" if brett <= 3 else ""
            daten[f"ergebnis_{brett}"] = "0.5" if brett <= 3 else ""
        response = self.client.post(f"/spiele/{self.match.pk}/aufstellung/", daten)
        self.assertRedirects(response, f"/spiele/{self.match.pk}/")
        self.assertEqual(LineupEntry.objects.filter(match=self.match).count(), 3)
        self.match.refresh_from_db()
        self.assertEqual(self.match.brettpunkte, (Decimal("1.5"), Decimal("1.5")))

    def test_spieldetail_zeigt_live_summe(self):
        LineupEntry.objects.create(match=self.match, brett=1, member=self.spieler[0], ergebnis="1")
        self.match.status_aktualisieren()
        response = self.client.get(f"/spiele/{self.match.pk}/")
        self.assertContains(response, "1.0 : 0.0")
        self.assertContains(response, "Aufstellung")
        self.assertContains(response, self.spieler[0].nachname)


class TabellenTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name="1. Mannschaft", liga="Bezirksliga", brettanzahl=2)

    def _spiel(self, gegner, brett_ergebnisse):
        """Legt ein gespieltes Ligaspiel mit den übergebenen Brettergebnissen an."""
        match = LeagueMatch.objects.create(
            team=self.team,
            datum=date(2026, 9, 1),
            gegner=gegner,
            brettanzahl=len(brett_ergebnisse),
            status=LeagueMatch.Status.GESPIELT,
        )
        for brett, ergebnis in enumerate(brett_ergebnisse, start=1):
            LineupEntry.objects.create(match=match, brett=brett, ergebnis=ergebnis)
        match.status_aktualisieren()
        return match

    def test_tabelle_zaehlt_mannschafts_und_brettpunkte(self):
        self._spiel("SV Sieg", ["1", "1"])      # 2,0 : 0,0  → Sieg (2 MP)
        self._spiel("SV Remis", ["0.5", "0.5"])  # 1,0 : 1,0  → Remis (1 MP)

        zeilen = tabelle("Bezirksliga")
        eigene = next(z for z in zeilen if z["name"] == "1. Mannschaft")
        gegner_remis = next(z for z in zeilen if z["name"] == "SV Remis")
        gegner_sieg = next(z for z in zeilen if z["name"] == "SV Sieg")

        self.assertEqual(eigene["spiele"], 2)
        self.assertEqual(eigene["mannschaftspunkte"], 3)
        self.assertEqual(eigene["brettpunkte"], Decimal("3.0"))
        self.assertEqual(eigene["gegner_brettpunkte"], Decimal("1.0"))
        self.assertEqual(eigene["brettdifferenz"], Decimal("2.0"))
        self.assertEqual(gegner_remis["mannschaftspunkte"], 1)
        self.assertEqual(gegner_sieg["mannschaftspunkte"], 0)
        self.assertEqual(zeilen[0]["name"], "1. Mannschaft", "Tabellenführer steht oben")
        self.assertEqual(zeilen[0]["platz"], 1)

    def test_tabelle_liste_rendert_ligen(self):
        self._spiel("SV Sieg", ["1", "1"])
        admin = make_user("vorstand", "admin")
        self.client.force_login(admin)
        response = self.client.get("/ligen/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bezirksliga")
        self.assertContains(response, "SV Sieg")
        self.assertContains(response, "wir")


class TeamCrudTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)

    def test_team_anlegen_aktualisieren_loeschen(self):
        response = self.client.post(
            "/mannschaften/neu/",
            {"name": "3. Mannschaft", "liga": "Kreisklasse", "altersklasse": "erwachsene",
             "brettanzahl": "4", "aktiv": "on"},
        )
        self.assertEqual(response.status_code, 302)
        team = Team.objects.get(name="3. Mannschaft")

        response = self.client.post(
            f"/mannschaften/{team.pk}/bearbeiten/",
            {"name": "3. Mannschaft", "liga": "Kreisklasse B", "altersklasse": "erwachsene",
             "brettanzahl": "4", "aktiv": "on"},
        )
        self.assertRedirects(response, f"/mannschaften/{team.pk}/")
        team.refresh_from_db()
        self.assertEqual(team.liga, "Kreisklasse B")

        response = self.client.post(
            f"/mannschaften/{team.pk}/loeschen/", HTTP_ACCEPT="application/json"
        )
        self.assertTrue(json.loads(response.content)["ok"])
        self.assertFalse(Team.objects.filter(pk=team.pk).exists())

    def test_team_mit_spielen_kann_nicht_geloescht_werden(self):
        team = Team.objects.create(name="1. Mannschaft", liga="Kreisliga", brettanzahl=4)
        LeagueMatch.objects.create(team=team, datum=date(2026, 9, 1), gegner="SV Test")
        response = self.client.post(
            f"/mannschaften/{team.pk}/loeschen/", HTTP_ACCEPT="application/json"
        )
        self.assertFalse(json.loads(response.content)["ok"])
        self.assertTrue(Team.objects.filter(pk=team.pk).exists())
