"""Turnierverwaltung: Anmeldung, Schweizer Paarung, Wertung und Export."""

import csv
import io
import json
from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase

from tournaments.models import Pairing, Participant, Tournament, teilnehmer_stand
from tournaments.pairing import generate_round


def make_admin(username="vorstand"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


def make_user_in_group(username, group_name):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


def turnier_mit_teilnehmern(anzahl=8, **kwargs):
    daten = {
        "name": "Testturnier",
        "datum": date(2026, 11, 14),
        "status": Tournament.Status.LAUFEND,
        "runden_anzahl": 3,
        "oeffentlich": True,
    }
    daten.update(kwargs)
    turnier = Tournament.objects.create(**daten)
    for index in range(anzahl):
        Participant.objects.create(
            tournament=turnier,
            name=f"Spieler {index}",
            twz=2000 - index * 50,
            verein="SC Königsspringer",
        )
    return turnier


class PaarungsTests(TestCase):
    def setUp(self):
        self.turnier = turnier_mit_teilnehmern(8)

    def test_drei_runden_ohne_doppelpaarungen(self):
        gespielte = set()
        for _ in range(3):
            runde, fehler = generate_round(self.turnier)
            self.assertIsNone(fehler)
            self.assertIsNotNone(runde)
            for paarung in runde.paarungen.all():
                self.assertIsNotNone(paarung.weiss)
                self.assertIsNotNone(paarung.schwarz)
                schluessel = frozenset((paarung.weiss_id, paarung.schwarz_id))
                self.assertNotIn(schluessel, gespielte, "Paarung darf sich nicht wiederholen")
                gespielte.add(schluessel)
                paarung.ergebnis = Pairing.Ergebnis.WEISS
                paarung.save(update_fields=["ergebnis"])

        self.assertEqual(self.turnier.runden.count(), 3)
        self.assertEqual(Pairing.objects.count(), 12)

    def test_ungerade_teilnehmerzahl_erhaelt_bye(self):
        turnier = turnier_mit_teilnehmern(7, name="Kleines Turnier")
        runde, _ = generate_round(turnier)
        byes = runde.paarungen.filter(ergebnis=Pairing.Ergebnis.BYE)
        self.assertEqual(byes.count(), 1)
        self.assertEqual(runde.paarungen.count(), 4)
        byespieler = byes.first().weiss
        self.assertEqual(byespieler.punkte, 1.0)

    def test_bye_wird_nicht_zweimal_vergeben(self):
        turnier = turnier_mit_teilnehmern(7, name="Kleines Turnier II")
        erste, _ = generate_round(turnier)
        zweite, _ = generate_round(turnier)
        byes = [
            byespieler.weiss_id
            for byespieler in list(erste.paarungen.filter(ergebnis=Pairing.Ergebnis.BYE))
            + list(zweite.paarungen.filter(ergebnis=Pairing.Ergebnis.BYE))
        ]
        self.assertEqual(len(byes), len(set(byes)), "Niemand erhält zweimal ein Bye")

    def test_zu_wenige_teilnehmer(self):
        turnier = Tournament.objects.create(name="Leer", datum=date(2026, 11, 1))
        Participant.objects.create(tournament=turnier, name="Allein")
        runde, fehler = generate_round(turnier)
        self.assertIsNone(runde)
        self.assertIn("mindestens zwei", fehler)

    def test_rundenlimit_wird_beachtet(self):
        for _ in range(3):
            generate_round(self.turnier)
        runde, fehler = generate_round(self.turnier)
        self.assertIsNone(runde)
        self.assertIn("Alle geplanten Runden", fehler)

    def test_wertung_mit_punkten_und_buchholz(self):
        runde, _ = generate_round(self.turnier)
        erste = runde.paarungen.first()
        erste.ergebnis = Pairing.Ergebnis.WEISS
        erste.save(update_fields=["ergebnis"])

        stand = teilnehmer_stand(self.turnier)
        sieger = stand[0]
        self.assertEqual(sieger.name, erste.weiss.name)
        self.assertEqual(sieger.aktuelle_punkte, 1.0)
        self.assertEqual(sieger.rang, 1)
        verlierer = next(t for t in stand if t.name == erste.schwarz.name)
        self.assertEqual(verlierer.aktuelle_punkte, 0.0)
        self.assertEqual(verlierer.aktuelle_buchholz, 1.0)


class TurnierverwaltungsTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.force_login(self.admin)
        self.turnier = turnier_mit_teilnehmern(6, status=Tournament.Status.ANMELDUNG)

    def test_anmeldung_ueber_ajax(self):
        response = self.client.post(
            f"/turniere/verwalten/{self.turnier.pk}/teilnehmer/",
            {"name": "Neue Spielerin", "verein": "SC Neu", "twz": "1700", "email": "", "geburtsjahr": "", "notiz": ""},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertTrue(self.turnier.teilnehmer.filter(name="Neue Spielerin").exists())

    def test_doppelte_anmeldung_wird_abgelehnt(self):
        response = self.client.post(
            f"/turniere/verwalten/{self.turnier.pk}/teilnehmer/",
            {"name": "Spieler 0", "verein": "", "twz": "", "email": "", "geburtsjahr": "", "notiz": ""},
            HTTP_ACCEPT="application/json",
        )
        self.assertFalse(json.loads(response.content)["ok"])
        self.assertEqual(self.turnier.teilnehmer.filter(name__iexact="Spieler 0").count(), 1)

    def test_startgeld_toggle(self):
        teilnehmer = self.turnier.teilnehmer.first()
        response = self.client.post(
            f"/turniere/verwalten/teilnehmer/{teilnehmer.pk}/startgeld/",
            {"startgeld_bezahlt": "1"},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["checked"])
        teilnehmer.refresh_from_db()
        self.assertTrue(teilnehmer.startgeld_bezahlt)

    def test_abmeldung_nach_paarung_wird_blockiert(self):
        generate_round(self.turnier)
        teilnehmer = self.turnier.teilnehmer.first()
        response = self.client.post(
            f"/turniere/verwalten/teilnehmer/{teilnehmer.pk}/loeschen/",
            HTTP_ACCEPT="application/json",
        )
        self.assertFalse(json.loads(response.content)["ok"])

    def test_rundenauslosung_und_ergebnis_ueber_ajax(self):
        response = self.client.post(
            f"/turniere/verwalten/{self.turnier.pk}/runde/", HTTP_ACCEPT="application/json"
        )
        self.assertTrue(json.loads(response.content)["ok"])
        paarung = Pairing.objects.filter(runde__tournament=self.turnier).first()

        response = self.client.post(
            f"/turniere/verwalten/paarung/{paarung.pk}/ergebnis/",
            {"ergebnis": "1-0"},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        paarung.refresh_from_db()
        self.assertEqual(paarung.ergebnis, Pairing.Ergebnis.WEISS)
        self.assertIn(paarung.weiss.name, daten["html"]["[data-stand-body]"])

    def test_letzte_runde_zuruecknehmen(self):
        generate_round(self.turnier)
        response = self.client.post(
            f"/turniere/verwalten/{self.turnier.pk}/runde/1/loeschen/",
            HTTP_ACCEPT="application/json",
        )
        self.assertTrue(json.loads(response.content)["ok"])
        self.assertEqual(self.turnier.runden.count(), 0)

    def test_turnier_abschliessen(self):
        response = self.client.post(
            f"/turniere/verwalten/{self.turnier.pk}/abschluss/", HTTP_ACCEPT="application/json"
        )
        self.assertTrue(json.loads(response.content)["ok"])
        self.turnier.refresh_from_db()
        self.assertEqual(self.turnier.status, Tournament.Status.BEENDET)

    def test_export_enthaelt_chessresults_struktur_und_rundenergebnisse(self):
        runde, _ = generate_round(self.turnier)
        for paarung in runde.paarungen.all():
            paarung.ergebnis = Pairing.Ergebnis.REMIS
            paarung.save(update_fields=["ergebnis"])

        response = self.client.get(f"/turniere/verwalten/{self.turnier.pk}/export.csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(f'filename="ergebnisse-{self.turnier.pk}.csv"', response["Content-Disposition"])

        inhalt = response.content.decode("utf-8-sig")
        zeilen = list(csv.reader(io.StringIO(inhalt), delimiter=";"))

        # [TRN] Sektion
        self.assertEqual(zeilen[0], ["[TRN]"])
        self.assertEqual(zeilen[1][0], "Kennung")
        self.assertEqual(zeilen[1][1], "Name")
        self.assertEqual(zeilen[2][0], "TRN")
        self.assertEqual(zeilen[2][1], self.turnier.name)

        # [ARB] Sektion
        self.assertEqual(zeilen[4], ["[ARB]"])
        self.assertEqual(zeilen[5][0], "Kennung")
        self.assertEqual(zeilen[6][0], "ARB")

        # [RAN] Sektion
        self.assertEqual(zeilen[8], ["[RAN]"])
        self.assertEqual(zeilen[9][0], "Kennung")
        self.assertEqual(zeilen[9][1], "Rang")
        self.assertIn("R1", zeilen[9])
        self.assertIn("Buchholz", zeilen[9])

        # Datenzeilen
        teilnehmer_zeilen = [z for z in zeilen[10:] if z and z[0] == "RAN"]
        self.assertEqual(len(teilnehmer_zeilen), 6)  # 6 Teilnehmer
        self.assertEqual(teilnehmer_zeilen[0][0], "RAN")
        self.assertEqual(teilnehmer_zeilen[0][1], "1")  # Rang 1

    def test_export_datenschutz_keine_privatdaten(self):
        # Teilnehmer mit E-Mail und Notiz
        p = self.turnier.teilnehmer.first()
        p.email = "geheim@privat.example"
        p.notiz = "Geheime Anmerkung"
        p.save(update_fields=["email", "notiz"])

        response = self.client.get(f"/turniere/verwalten/{self.turnier.pk}/export.csv")
        inhalt = response.content.decode("utf-8-sig")
        self.assertNotIn("geheim@privat.example", inhalt)
        self.assertNotIn("Geheime Anmerkung", inhalt)

    def test_export_deterministisch(self):
        generate_round(self.turnier)
        r1 = self.client.get(f"/turniere/verwalten/{self.turnier.pk}/export.csv")
        r2 = self.client.get(f"/turniere/verwalten/{self.turnier.pk}/export.csv")
        self.assertEqual(r1.content, r2.content)

    def test_export_und_druck_rollen_berechtigungen(self):
        # Negativtests je Rolle nach Berechtigungsmatrix §3.8
        kapitaen = make_user_in_group("kapitaen_user", "kapitaen")
        mitglied = make_user_in_group("mitglied_user", "mitglied")

        for user in (kapitaen, mitglied):
            self.client.force_login(user)
            resp_csv = self.client.get(f"/turniere/verwalten/{self.turnier.pk}/export.csv")
            self.assertEqual(resp_csv.status_code, 403, f"Rolle {user.groups.first().name} darf CSV nicht exportieren")
            resp_print = self.client.get(f"/turniere/verwalten/{self.turnier.pk}/druck/")
            self.assertEqual(resp_print.status_code, 403, f"Rolle {user.groups.first().name} darf Druckansicht nicht aufrufen")

        # Gast / Anonym
        self.client.logout()
        resp_csv = self.client.get(f"/turniere/verwalten/{self.turnier.pk}/export.csv")
        self.assertEqual(resp_csv.status_code, 302)
        resp_print = self.client.get(f"/turniere/verwalten/{self.turnier.pk}/druck/")
        self.assertEqual(resp_print.status_code, 302)

    def test_druckansicht(self):
        generate_round(self.turnier)
        response = self.client.get(f"/turniere/verwalten/{self.turnier.pk}/druck/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ergebnisliste")
        self.assertContains(response, "Buchholz")
        self.assertContains(response, "Drucken")


class OeffentlicheAnmeldungTests(TestCase):
    def setUp(self):
        self.turnier = turnier_mit_teilnehmern(0, status=Tournament.Status.ANMELDUNG)

    def test_gast_anmeldung_ohne_login(self):
        response = self.client.post(
            f"/turniere/{self.turnier.pk}/",
            {"name": "Gast Spielerin", "verein": "SC Gast", "twz": "1600",
             "geburtsjahr": "1995", "email": "gast@example.org"},
        )
        self.assertRedirects(response, f"/turniere/{self.turnier.pk}/")
        teilnehmer = self.turnier.teilnehmer.get()
        self.assertEqual(teilnehmer.name, "Gast Spielerin")
        self.assertFalse(teilnehmer.startgeld_bezahlt)

    def test_doppelte_gast_anmeldung_zeigt_hinweis(self):
        self.turnier.teilnehmer.create(name="Gast Spielerin")
        response = self.client.post(
            f"/turniere/{self.turnier.pk}/",
            {"name": "Gast Spielerin", "verein": "", "twz": "", "geburtsjahr": "", "email": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bereits angemeldet")
        self.assertEqual(self.turnier.teilnehmer.count(), 1)

    def test_geschlossene_anmeldung(self):
        self.turnier.status = Tournament.Status.BEENDET
        self.turnier.save()
        response = self.client.post(
            f"/turniere/{self.turnier.pk}/",
            {"name": "Zu spät", "verein": "", "twz": "", "geburtsjahr": "", "email": ""},
        )
        self.assertContains(response, "Anmeldung geschlossen")
        self.assertFalse(self.turnier.teilnehmer.exists())

    def test_anmeldeschluss_wird_beachtet(self):
        self.turnier.anmeldeschluss = date(2020, 1, 1)
        self.turnier.save()
        self.assertFalse(self.turnier.anmeldung_offen)

    def test_angemeldetes_mitglied_wird_verknuepft(self):
        from members.models import Member

        user = User.objects.create_user("p1", password="x")
        group, _ = Group.objects.get_or_create(name="mitglied")
        user.groups.add(group)
        member = Member.objects.create(
            vorname="Lena", nachname="Fischer", eintrittsdatum=date(2020, 1, 1), user=user
        )
        self.client.force_login(user)
        self.client.post(
            f"/turniere/{self.turnier.pk}/",
            {"name": "Lena Fischer", "verein": "", "twz": "", "geburtsjahr": "", "email": ""},
        )
        teilnehmer = self.turnier.teilnehmer.get()
        self.assertEqual(teilnehmer.member, member)
