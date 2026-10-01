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

    def _spiel(self, gegner, brett_ergebnisse, team=None, status=LeagueMatch.Status.GESPIELT):
        """Legt ein Ligaspiel mit den übergebenen Brettergebnissen an."""
        match = LeagueMatch.objects.create(
            team=team or self.team,
            datum=date(2026, 9, 1),
            gegner=gegner,
            brettanzahl=len(brett_ergebnisse),
            status=status,
        )
        for brett, ergebnis in enumerate(brett_ergebnisse, start=1):
            LineupEntry.objects.create(match=match, brett=brett, ergebnis=ergebnis)
        match.status_aktualisieren()
        if status != LeagueMatch.Status.GESPIELT:
            match.status = status
            match.save(update_fields=["status"])
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
        self.assertEqual(eigene["buchholz"], 1)  # SV Sieg (0 MP) + SV Remis (1 MP)
        self.assertEqual(gegner_remis["mannschaftspunkte"], 1)
        self.assertEqual(gegner_remis["buchholz"], 3)  # Gegen 1. Mannschaft (3 MP)
        self.assertEqual(gegner_sieg["mannschaftspunkte"], 0)
        self.assertEqual(gegner_sieg["buchholz"], 3)  # Gegen 1. Mannschaft (3 MP)
        self.assertEqual(zeilen[0]["name"], "1. Mannschaft", "Tabellenführer steht oben")
        self.assertEqual(zeilen[0]["platz"], 1)

    def test_tabelle_4_mannschaften_3_spiele_inklusive_buchholz(self):
        # 4 Mannschaften × 3 Spiele mit bekanntem Ergebnis (Akzeptanzkriterium T18)
        # 1. Mannschaft spielt gegen 3 Gegner
        self._spiel("SF Turm", ["1", "1"])        # 1. Mannschaft gewinnt 2:0 (2 MP vs 0 MP)
        self._spiel("SK Springer", ["0.5", "0.5"])  # 1. Mannschaft spielt 1:1 Remis (1 MP vs 1 MP)
        self._spiel("SC Läufer", ["0", "0"])      # 1. Mannschaft verliert 0:2 (0 MP vs 2 MP)

        zeilen = tabelle("Bezirksliga")
        self.assertEqual(len(zeilen), 4)

        tabelle_dict = {z["name"]: z for z in zeilen}

        # 1. Mannschaft: 3 MP, 3.0 BP, Gegner: SF Turm (0), SK Springer (1), SC Läufer (2) → BH = 3
        m1 = tabelle_dict["1. Mannschaft"]
        self.assertEqual(m1["spiele"], 3)
        self.assertEqual(m1["mannschaftspunkte"], 3)
        self.assertEqual(m1["brettpunkte"], Decimal("3.0"))
        self.assertEqual(m1["buchholz"], 3)
        self.assertEqual(m1["platz"], 1)

        # SC Läufer: 1 Spiel, 2 MP, 2.0 BP, Gegner: 1. Mannschaft (3 MP) → BH = 3
        laeufer = tabelle_dict["SC Läufer"]
        self.assertEqual(laeufer["spiele"], 1)
        self.assertEqual(laeufer["mannschaftspunkte"], 2)
        self.assertEqual(laeufer["brettpunkte"], Decimal("2.0"))
        self.assertEqual(laeufer["buchholz"], 3)
        self.assertEqual(laeufer["platz"], 2)

        # SK Springer: 1 Spiel, 1 MP, 1.0 BP, Gegner: 1. Mannschaft (3 MP) → BH = 3
        springer = tabelle_dict["SK Springer"]
        self.assertEqual(springer["spiele"], 1)
        self.assertEqual(springer["mannschaftspunkte"], 1)
        self.assertEqual(springer["brettpunkte"], Decimal("1.0"))
        self.assertEqual(springer["buchholz"], 3)
        self.assertEqual(springer["platz"], 3)

        # SF Turm: 1 Spiel, 0 MP, 0.0 BP, Gegner: 1. Mannschaft (3 MP) → BH = 3
        turm = tabelle_dict["SF Turm"]
        self.assertEqual(turm["spiele"], 1)
        self.assertEqual(turm["mannschaftspunkte"], 0)
        self.assertEqual(turm["brettpunkte"], Decimal("0.0"))
        self.assertEqual(turm["buchholz"], 3)
        self.assertEqual(turm["platz"], 4)

        # Reihenfolge in der Tabelle
        self.assertEqual([z["name"] for z in zeilen], ["1. Mannschaft", "SC Läufer", "SK Springer", "SF Turm"])

    def test_buchholz_als_tiebreak_bei_gleichen_mannschafts_und_brettpunkten(self):
        # Zwei eigene Teams in derselben Liga
        team_a = Team.objects.create(name="Team A", liga="Bezirksliga", brettanzahl=2)
        team_b = Team.objects.create(name="Team B", liga="Bezirksliga", brettanzahl=2)

        # Team A gewinnt gegen SK Stark (4 MP)
        # SK Stark hat zuvor gegen 1. Mannschaft gewonnen (2 MP)
        self._spiel("SK Stark", ["0", "0"])  # 1. Mannschaft verliert gegen SK Stark → Stark hat 2 MP
        self._spiel("SK Stark", ["1", "1"], team=team_a)  # Team A schlägt SK Stark (2 MP) → Stark hat insgesamt 2 MP, Team A hat 2 MP, 2 BP
        # Team B schlägt SK Schwach (0 MP)
        self._spiel("SK Schwach", ["1", "1"], team=team_b)  # Team B gewinnt 2:0 → Team B hat 2 MP, 2 BP

        zeilen = tabelle("Bezirksliga")
        tabelle_dict = {z["name"]: z for z in zeilen}

        # Team A und Team B haben beide 2 MP und 2.0 BP
        self.assertEqual(tabelle_dict["Team A"]["mannschaftspunkte"], 2)
        self.assertEqual(tabelle_dict["Team B"]["mannschaftspunkte"], 2)
        self.assertEqual(tabelle_dict["Team A"]["brettpunkte"], Decimal("2.0"))
        self.assertEqual(tabelle_dict["Team B"]["brettpunkte"], Decimal("2.0"))

        # Team A spielte gegen SK Stark (2 MP) → BH = 2
        # Team B spielte gegen SK Schwach (0 MP) → BH = 0
        self.assertEqual(tabelle_dict["Team A"]["buchholz"], 2)
        self.assertEqual(tabelle_dict["Team B"]["buchholz"], 0)

        # Team A muss dank höherem Buchholz vor Team B stehen
        self.assertLess(tabelle_dict["Team A"]["platz"], tabelle_dict["Team B"]["platz"])

    def test_ungespielte_und_abgesagte_spiele_zaehlen_nicht_in_tabelle(self):
        # Negativtest: geplante, aufgestellte und abgesagte Spiele fließen nicht ein
        self._spiel("SV Gespielt", ["1", "1"], status=LeagueMatch.Status.GESPIELT)
        self._spiel("SV Geplant", ["1", "1"], status=LeagueMatch.Status.GEPLANT)
        self._spiel("SV Aufgestellt", ["1", "1"], status=LeagueMatch.Status.AUFGESTELLT)
        self._spiel("SV Abgesagt", ["1", "1"], status=LeagueMatch.Status.ABGESAGT)

        zeilen = tabelle("Bezirksliga")
        tabelle_dict = {z["name"]: z for z in zeilen}

        # Nur SV Gespielt und 1. Mannschaft dürfen gezählt werden
        self.assertIn("SV Gespielt", tabelle_dict)
        self.assertNotIn("SV Geplant", tabelle_dict)
        self.assertNotIn("SV Aufgestellt", tabelle_dict)
        self.assertNotIn("SV Abgesagt", tabelle_dict)

        m1 = tabelle_dict["1. Mannschaft"]
        self.assertEqual(m1["spiele"], 1)
        self.assertEqual(m1["mannschaftspunkte"], 2)
        self.assertEqual(m1["brettpunkte"], Decimal("2.0"))
        self.assertEqual(m1["buchholz"], 0)

    def test_tabelle_liste_rendert_ligen_und_buchholz_spalte(self):
        self._spiel("SV Sieg", ["1", "1"])
        admin = make_user("vorstand", "admin")
        self.client.force_login(admin)
        response = self.client.get("/ligen/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bezirksliga")
        self.assertContains(response, "SV Sieg")
        self.assertContains(response, "wir")
        self.assertContains(response, "Buchholz")


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


class ICalFeedTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.kapitaen_user = make_user("k1", "kapitaen")
        self.kapitaen = make_member("Karla", "Kapitän", user=self.kapitaen_user)
        self.mitglied_user = make_user("m1", "mitglied")
        self.mitglied = make_member("Dana", "Dorn", user=self.mitglied_user)

        self.team1 = Team.objects.create(
            name="1. Mannschaft", liga="Bezirksliga", brettanzahl=8, kapitaen=self.kapitaen
        )
        self.team2 = Team.objects.create(
            name="2. Mannschaft", liga="Kreisklasse", brettanzahl=6
        )

        from datetime import time
        self.match1 = LeagueMatch.objects.create(
            team=self.team1, datum=date(2026, 10, 10), uhrzeit=time(14, 0),
            gegner="SV Gegner 1", heimspiel=True, ort="Bürgerhaus Raum 1",
            runde="1. Runde", status=LeagueMatch.Status.GEPLANT, bemerkung="Pünktlich da sein"
        )
        self.match2 = LeagueMatch.objects.create(
            team=self.team1, datum=date(2026, 10, 24), uhrzeit=None,
            gegner="SV Gegner 2", heimspiel=False, ort="Auswärtsspielort",
            runde="2. Runde", status=LeagueMatch.Status.ABGESAGT
        )
        self.match3 = LeagueMatch.objects.create(
            team=self.team2, datum=date(2026, 11, 7), uhrzeit=time(10, 0),
            gegner="SV Team 2 Gegner", heimspiel=True, ort="Vereinsheim",
            runde="1. Spieltag", status=LeagueMatch.Status.GEPLANT
        )

        # Aufstellung mit Personendaten für match1
        LineupEntry.objects.create(match=self.match1, brett=1, member=self.mitglied, gegner_name="Fremder Spieler")

    def test_feed_mannschaft_enthaelt_nur_spiele_der_mannschaft_ohne_login(self):
        # Client ist nicht eingeloggt (Zugriff rein über geheimen Token-Link)
        url = f"/mannschaften/{self.team1.pk}/ical/{self.team1.ical_token}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/calendar"))
        content = response.content.decode("utf-8")

        self.assertIn("BEGIN:VCALENDAR", content)
        self.assertIn("VERSION:2.0", content)
        self.assertIn("1. Mannschaft – Ligaspiele", content)
        self.assertIn("SV Gegner 1 (Heimspiel)", content)
        self.assertIn("SV Gegner 2 (Auswärtsspiel)", content)
        self.assertNotIn("SV Team 2 Gegner", content)
        self.assertIn("Bürgerhaus Raum 1", content)
        self.assertIn("DTSTART:20261010T140000", content)
        self.assertIn("DTSTART;VALUE=DATE:20261024", content)
        self.assertIn("END:VCALENDAR", content)

    def test_feed_gesamt_enthaelt_alle_mannschaften(self):
        from teams.models import LeagueCalendarFeed
        feed_token = LeagueCalendarFeed.get_token()
        url = f"/ical/gesamt/{feed_token}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        self.assertIn("Alle Ligaspiele", content)
        self.assertIn("SV Gegner 1", content)
        self.assertIn("SV Team 2 Gegner", content)

    def test_negativ_ungueltiger_oder_fehlender_token_liefert_404(self):
        # Ungültiger Token für existierendes Team
        res1 = self.client.get(f"/mannschaften/{self.team1.pk}/ical/ungueltiger_token/")
        self.assertEqual(res1.status_code, 404)

        # Ungültiger Token für nicht existierendes Team (kein Information Leak)
        res2 = self.client.get("/mannschaften/99999/ical/ungueltiger_token/")
        self.assertEqual(res2.status_code, 404)

        # Ungültiger Token für Gesamtfeed
        res3 = self.client.get("/ical/gesamt/falscher_token/")
        self.assertEqual(res3.status_code, 404)

    def test_feed_enthaelt_keine_aufstellungs_und_keine_personendaten(self):
        url = f"/mannschaften/{self.team1.pk}/ical/{self.team1.ical_token}/"
        response = self.client.get(url)
        content = response.content.decode("utf-8")

        # Weder Mitgliedsname, noch Kapitän, noch Gegner am Brett, noch Aufstellungswort
        self.assertNotIn("Dana", content)
        self.assertNotIn("Dorn", content)
        self.assertNotIn("Karla", content)
        self.assertNotIn("Kapitän", content)
        self.assertNotIn("Fremder Spieler", content)
        self.assertNotIn("Lineup", content)
        self.assertNotIn("Aufstellung", content)

    def test_abgesagtes_spiel_wird_als_status_cancelled_ausgegeben(self):
        url = f"/mannschaften/{self.team1.pk}/ical/{self.team1.ical_token}/"
        response = self.client.get(url)
        content = response.content.decode("utf-8")

        # match1 ist GEPLANT -> CONFIRMED
        self.assertIn("STATUS:CONFIRMED", content)
        # match2 ist ABGESAGT -> STATUS:CANCELLED (nicht weggelassen!)
        self.assertIn("STATUS:CANCELLED", content)
        self.assertIn("SV Gegner 2", content)

    def test_token_erneuerung_macht_alte_links_ungueltig(self):
        alter_token = self.team1.ical_token
        alt_url = f"/mannschaften/{self.team1.pk}/ical/{alter_token}/"
        self.assertEqual(self.client.get(alt_url).status_code, 200)

        # Admin erneuert das Token
        self.client.force_login(self.admin)
        response = self.client.post(f"/mannschaften/{self.team1.pk}/ical-token-erneuern/")
        self.assertRedirects(response, f"/mannschaften/{self.team1.pk}/")

        self.team1.refresh_from_db()
        self.assertNotEqual(self.team1.ical_token, alter_token)

        # Alter Link liefert nun 404
        self.client.logout()
        self.assertEqual(self.client.get(alt_url).status_code, 404)

        # Neuer Link liefert 200
        neu_url = f"/mannschaften/{self.team1.pk}/ical/{self.team1.ical_token}/"
        self.assertEqual(self.client.get(neu_url).status_code, 200)

    def test_gesamt_token_erneuerung_macht_alten_link_ungueltig(self):
        from teams.models import LeagueCalendarFeed
        alter_token = LeagueCalendarFeed.get_token()
        alt_url = f"/ical/gesamt/{alter_token}/"
        self.assertEqual(self.client.get(alt_url).status_code, 200)

        self.client.force_login(self.admin)
        response = self.client.post("/ical/gesamt/token-erneuern/")
        self.assertRedirects(response, "/spiele/")

        neuer_token = LeagueCalendarFeed.get_token()
        self.assertNotEqual(alter_token, neuer_token)

        self.client.logout()
        self.assertEqual(self.client.get(alt_url).status_code, 404)
        self.assertEqual(self.client.get(f"/ical/gesamt/{neuer_token}/").status_code, 200)

    def test_negativ_nicht_admin_kann_token_nicht_erneuern(self):
        self.client.force_login(self.kapitaen_user)
        res1 = self.client.post(f"/mannschaften/{self.team1.pk}/ical-token-erneuern/")
        self.assertEqual(res1.status_code, 403)

        res2 = self.client.post("/ical/gesamt/token-erneuern/")
        self.assertEqual(res2.status_code, 403)

        self.client.force_login(self.mitglied_user)
        res3 = self.client.post(f"/mannschaften/{self.team1.pk}/ical-token-erneuern/")
        self.assertEqual(res3.status_code, 403)

    def test_assert_num_queries_fuer_feeds(self):
        # Genau 2 Queries für Team-Feed: 1 Team-Lookup + 1 Match-Abfrage mit select_related
        with self.assertNumQueries(2):
            res = self.client.get(f"/mannschaften/{self.team1.pk}/ical/{self.team1.ical_token}/")
            self.assertEqual(res.status_code, 200)

        from teams.models import LeagueCalendarFeed
        feed_token = LeagueCalendarFeed.get_token()
        # Genau 2 Queries für Gesamt-Feed: 1 Feed-Lookup + 1 Match-Abfrage mit select_related
        with self.assertNumQueries(2):
            res = self.client.get(f"/ical/gesamt/{feed_token}/")
            self.assertEqual(res.status_code, 200)

