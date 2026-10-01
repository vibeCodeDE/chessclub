"""Durchgängige Arbeitsabläufe: die AJAX-Verträge, auf denen das UI aufsetzt.

Die Tests prüfen genau die Antwortfelder, die static/js/app.js auswertet
(``patch``, ``html``, ``classes``, ``reload``, ``remove_selector``).
"""

import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase

from cashbook.models import CashEntry
from dues.models import FeeAmount, FeeCategory, MembershipFee, Payment
from members.models import ChangeRequest, Member
from teams.models import LeagueMatch, LineupEntry, Team
from tournaments.models import Pairing, Participant, Tournament


def make_user(username, gruppe):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name=gruppe)
    user.groups.add(group)
    return user


def ajax_post(client, url, daten=None):
    return client.post(url, daten or {}, HTTP_ACCEPT="application/json", HTTP_X_REQUESTED_WITH="fetch")


def als_json(antwort):
    return json.loads(antwort.content.decode())


class AjaxVertragTests(TestCase):
    """Jeder Schreib-Endpunkt antwortet mit dem vereinbarten JSON-Format."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=self.kategorie, jahr=date.today().year, betrag=Decimal("90.00"))
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1),
            beitragskategorie=self.kategorie,
        )
        self.fee = MembershipFee.objects.create(
            member=self.member, jahr=date.today().year, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )

    def test_mitglied_anlegen_und_statuswechsel(self):
        antwort = ajax_post(self.client, "/mitglieder/neu/", {
            "vorname": "Nele", "nachname": "Neumann", "eintrittsdatum": "2026-09-01",
            "status": "aktiv", "email_opt_in": "on",
        })
        daten = als_json(antwort)
        self.assertTrue(daten["ok"])
        self.assertIn("/mitglieder/", daten["redirect"])
        neu = Member.objects.get(nachname="Neumann")

        antwort = ajax_post(self.client, f"/mitglieder/{neu.pk}/status/", {"status": "passiv"})
        daten = als_json(antwort)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"][f"[data-status-text='{neu.pk}']"], "Passiv")
        neu.refresh_from_db()
        self.assertEqual(neu.status, Member.Status.PASSIV)

    def test_zahlung_erfassen_aktualisiert_posten_und_kasse(self):
        antwort = ajax_post(self.client, f"/beitraege/posten/{self.fee.pk}/zahlung/", {
            "betrag": "90.00", "datum": "2026-03-01", "art": "ueberweisung", "notiz": "Bar erhalten",
        })
        daten = als_json(antwort)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"][f"[data-fee-open='{self.fee.pk}']"], "0.00 €")
        self.assertIn("[data-payment-rows]", daten["html"])
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.status, MembershipFee.Status.BEZAHLT)
        self.assertTrue(Payment.objects.filter(fee=self.fee).exists())
        self.assertTrue(CashEntry.objects.filter(kategorie=CashEntry.Kategorie.BEITRAEGE).exists())

    def test_mahnung_und_mahnbrief(self):
        antwort = ajax_post(self.client, f"/beitraege/mahnwesen/{self.fee.pk}/mahnung/", {"gebuehr": "5.00"})
        daten = als_json(antwort)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"][f"[data-mahnstufe='{self.fee.pk}']"], "1. Mahnung")

        brief = self.client.get(f"/beitraege/mahnwesen/{self.fee.pk}/brief/")
        self.assertEqual(brief.status_code, 200)
        self.assertContains(brief, "Anna")
        self.assertContains(brief, "1. Mahnung")

    def test_aufstellung_autosave_liefert_brettpunkte(self):
        team = Team.objects.create(name="1. Mannschaft", liga="Kreisliga", brettanzahl=4)
        match = LeagueMatch.objects.create(team=team, datum=date(2026, 10, 10), gegner="SV Test", brettanzahl=4)
        antwort = ajax_post(self.client, f"/spiele/{match.pk}/brett/1/", {
            "member": self.member.pk, "gegner_name": "Gegner", "ergebnis": "1",
        })
        daten = als_json(antwort)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"]["[data-brettpunkte]"], "1.0 : 0.0")
        self.assertEqual(daten["patch"]["[data-mannschaftspunkte]"], "Sieg")
        self.assertTrue(LineupEntry.objects.filter(match=match, brett=1).exists())

    def test_turnier_auslosen_und_ergebnis_eintragen(self):
        turnier = Tournament.objects.create(
            name="Testturnier", datum=date(2026, 11, 1), status=Tournament.Status.ANMELDUNG,
            runden_anzahl=3, oeffentlich=True,
        )
        for index in range(4):
            Participant.objects.create(tournament=turnier, name=f"Spieler {index}")

        antwort = ajax_post(self.client, f"/turniere/verwalten/{turnier.pk}/runde/")
        self.assertTrue(als_json(antwort)["ok"])
        self.assertEqual(turnier.runden.count(), 1)

        paarung = Pairing.objects.filter(runde__tournament=turnier).first()
        antwort = ajax_post(
            self.client,
            f"/turniere/verwalten/paarung/{paarung.pk}/ergebnis/",
            {"ergebnis": Pairing.Ergebnis.WEISS},
        )
        daten = als_json(antwort)
        self.assertTrue(daten["ok"])
        # Das Brett zeigt die Ergebnistext-Anzeige, die Wertungstabelle die Punkte
        paarung.refresh_from_db()
        self.assertEqual(daten["patch"][f"[data-punkte='{paarung.pk}']"], "Weiß gewinnt")
        self.assertEqual(daten["patch"][f"[data-stand-punkte='{paarung.weiss.pk}']"], "1.0")
        self.assertEqual(daten["patch"][f"[data-stand-punkte='{paarung.schwarz.pk}']"], "0.0")
        self.assertIn("[data-stand-body]", daten["html"])
        self.assertIn(paarung.weiss.name, daten["html"]["[data-stand-body]"])

    def test_startgeld_toggle(self):
        turnier = Tournament.objects.create(name="Rapid", datum=date(2026, 11, 1))
        teilnehmer = Participant.objects.create(tournament=turnier, name="Gast")
        antwort = ajax_post(
            self.client, f"/turniere/verwalten/teilnehmer/{teilnehmer.pk}/startgeld/", {"startgeld_bezahlt": "1"}
        )
        daten = als_json(antwort)
        self.assertTrue(daten["ok"])
        self.assertTrue(daten["checked"])
        self.assertEqual(daten["patch"][f"[data-startgeld-text='{teilnehmer.pk}']"], "bezahlt")

    def test_kuendigung_veroeffentlichen_und_loeschen(self):
        from comms.models import NewsPost

        post = NewsPost.objects.create(titel="Neuigkeit", text="Text")
        antwort = ajax_post(self.client, f"/ankuendigungen/{post.pk}/veroeffentlichen/")
        daten = als_json(antwort)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"][f"[data-news-status='{post.pk}']"], "Veröffentlicht")

        antwort = ajax_post(self.client, f"/ankuendigungen/{post.pk}/loeschen/")
        daten = als_json(antwort)
        self.assertEqual(daten["remove_selector"], f"[data-row='news-{post.pk}']")
        self.assertFalse(NewsPost.objects.filter(pk=post.pk).exists())

    def test_kassenbuchung_anlegen_und_stornieren(self):
        antwort = ajax_post(self.client, "/kasse/neu/", {
            "art": CashEntry.Art.AUSGABE, "kategorie": CashEntry.Kategorie.MATERIAL,
            "betrag": "49.90", "datum": "2026-05-04", "beschreibung": "Turnieruhren", "belegnummer": "B-12",
        })
        self.assertTrue(als_json(antwort)["ok"])
        buchung = CashEntry.objects.get(beschreibung="Turnieruhren")
        self.assertEqual(buchung.erfasst_von, self.admin)

        antwort = ajax_post(self.client, f"/kasse/{buchung.pk}/storno/", {"grund": "Fehlkauf"})
        self.assertTrue(als_json(antwort)["ok"])
        # Finanzdaten werden nicht hart gelöscht, sondern per Gegenbuchung storniert
        self.assertTrue(CashEntry.objects.filter(pk=buchung.pk).exists())
        self.assertTrue(buchung.ist_storniert)
        gegen = CashEntry.objects.get(storno_von=buchung)
        self.assertEqual(gegen.betrag, Decimal("-49.90"))
        self.assertIn("Fehlkauf", gegen.beschreibung)

    def test_aenderungswunsch_freigeben(self):
        wunsch = ChangeRequest.objects.create(
            member=self.member, feld="telefon", wunschwert="030 999999",
            eingereicht_von=self.admin,
        )
        antwort = ajax_post(self.client, f"/mitglieder/wuensche/{wunsch.pk}/freigabe/")
        self.assertTrue(als_json(antwort)["ok"])
        self.member.refresh_from_db()
        wunsch.refresh_from_db()
        self.assertEqual(self.member.telefon, "030 999999")
        self.assertEqual(wunsch.status, ChangeRequest.Status.FREIGEGEBEN)

    def test_kuendigung_nur_admin(self):
        spieler = make_user("p1", "mitglied")
        self.client.force_login(spieler)
        for url, daten in [
            ("/mitglieder/neu/", {"vorname": "X", "nachname": "Y", "eintrittsdatum": "2026-01-01"}),
            ("/beitraege/lauf/", {"jahr": "2027"}),
            ("/kasse/neu/", {"art": "einnahme", "kategorie": "sonstiges", "betrag": "5", "datum": "2026-01-01", "beschreibung": "x"}),
        ]:
            with self.subTest(url=url):
                self.assertEqual(ajax_post(self.client, url, daten).status_code, 403)


class FormularFallbackTests(TestCase):
    """Ohne JavaScript müssen die klassischen Formular-POSTs genauso funktionieren."""

    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)

    def test_zahlung_ohne_javascript(self):
        kategorie = FeeCategory.objects.create(name="Ermäßigt")
        FeeAmount.objects.create(kategorie=kategorie, jahr=2026, betrag=Decimal("60.00"))
        member = Member.objects.create(
            vorname="Bodo", nachname="Bauer", eintrittsdatum=date(2020, 1, 1),
            beitragskategorie=kategorie,
        )
        fee = MembershipFee.objects.create(
            member=member, jahr=2026, kategorie_name="Ermäßigt",
            betrag=Decimal("60.00"), faellig_am=date(2026, 1, 31),
        )
        antwort = self.client.post(
            f"/beitraege/posten/{fee.pk}/zahlung/",
            {"betrag": "60.00", "datum": "2026-03-01", "art": "bar", "notiz": ""},
        )
        self.assertEqual(antwort.status_code, 302)
        fee.refresh_from_db()
        self.assertEqual(fee.status, MembershipFee.Status.BEZAHLT)

    def test_beitragslauf_ohne_javascript(self):
        antwort = self.client.post("/beitraege/lauf/", {"jahr": "2027", "faellig_am": "2027-01-31"})
        self.assertEqual(antwort.status_code, 302)

    def test_oeffentliche_anmeldung_ohne_javascript(self):
        klient = Client()
        turnier = Tournament.objects.create(
            name="Offenes Blitzturnier", datum=date(2026, 12, 5),
            status=Tournament.Status.ANMELDUNG, oeffentlich=True, runden_anzahl=5,
        )
        antwort = klient.post(f"/turniere/{turnier.pk}/", {
            "name": "Gast Spielerin", "verein": "SV Gast", "twz": "1500",
            "geburtsjahr": "1998", "email": "gast@example.org",
        })
        self.assertEqual(antwort.status_code, 302)
        self.assertTrue(turnier.teilnehmer.filter(name="Gast Spielerin").exists())
        # Sichtbar auf der öffentlichen Turnierseite
        seite = klient.get(f"/turniere/{turnier.pk}/")
        self.assertContains(seite, "Gast Spielerin")
