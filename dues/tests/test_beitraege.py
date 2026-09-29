"""Beitragslauf, Zahlungen, Mahnwesen und Mandate."""

import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from cashbook.models import CashEntry
from dues.models import DunningLetter, FeeCategory, MembershipFee, Payment, SepaMandate
from dues.services import beitragslauf, mahnung_erstellen, zahlung_erfassen
from members.models import Member


def make_admin(username="vorstand"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


class BeitragslaufTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.erwachsene = FeeCategory.objects.create(name="Erwachsene", betrag=Decimal("90.00"))
        self.jugend = FeeCategory.objects.create(name="Jugendliche", betrag=Decimal("45.00"))
        for index in range(3):
            Member.objects.create(
                vorname=f"Anna{index}", nachname=f"Meier{index}",
                eintrittsdatum=date(2020, 1, 1), beitragskategorie=self.erwachsene,
            )
        Member.objects.create(
            vorname="Passiv", nachname="Person",
            eintrittsdatum=date(2020, 1, 1), status=Member.Status.PASSIV,
            beitragskategorie=self.erwachsene,
        )
        Member.objects.create(vorname="Ohne", nachname="Kategorie", eintrittsdatum=date(2020, 1, 1))

    def test_lauf_erzeugt_nur_fuer_aktive_mit_kategorie(self):
        ergebnis = beitragslauf(2026)
        self.assertEqual(ergebnis["angelegt"], 3)
        self.assertEqual(ergebnis["summe"], Decimal("270.00"))
        self.assertEqual(ergebnis["ohne_kategorie"], 1)
        self.assertEqual(MembershipFee.objects.filter(jahr=2026).count(), 3)

    def test_lauf_ist_idempotent(self):
        beitragslauf(2026)
        zweiter = beitragslauf(2026)
        self.assertEqual(zweiter["angelegt"], 0)
        self.assertEqual(zweiter["uebersprungen"], 3)
        self.assertEqual(MembershipFee.objects.filter(jahr=2026).count(), 3)

    def test_ajax_lauf_meldet_ergebnis(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/beitraege/lauf/", {"jahr": "2027"}, HTTP_ACCEPT="application/json"
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertIn("3 Posten", daten["message"])


class ZahlungTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1)
        )
        self.fee = MembershipFee.objects.create(
            member=self.member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )

    def test_teilzahlung_setzt_status_und_bucht_kasse(self):
        zahlung_erfassen(self.fee, betrag=Decimal("40.00"), benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.status, MembershipFee.Status.TEILWEISE)
        self.assertEqual(self.fee.offener_betrag, Decimal("50.00"))
        self.assertEqual(self.fee.bezahlter_betrag, Decimal("40.00"))
        eintrag = CashEntry.objects.get()
        self.assertEqual(eintrag.art, CashEntry.Art.EINNAHME)
        self.assertEqual(eintrag.betrag, Decimal("40.00"))
        self.assertEqual(eintrag.kategorie, CashEntry.Kategorie.BEITRAEGE)

    def test_vollzahlung_schliesst_posten(self):
        zahlung_erfassen(self.fee, betrag=Decimal("90.00"), benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.status, MembershipFee.Status.BEZAHLT)
        self.assertEqual(self.fee.offener_betrag, Decimal("0.00"))
        self.assertEqual(self.fee.fortschritt_prozent, 100)

    def test_ajax_zahlung_aktualisiert_zeile(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/beitraege/posten/{self.fee.pk}/zahlung/",
            {"betrag": "90.00", "datum": "2026-03-01", "art": "ueberweisung", "notiz": "Test"},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"][f"[data-fee-open='{self.fee.pk}']"], "0.00 €")
        self.assertEqual(Payment.objects.count(), 1)

    def test_zahlung_validiert_betrag(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/beitraege/posten/{self.fee.pk}/zahlung/",
            {"betrag": "0", "datum": "2026-03-01", "art": "bar"},
            HTTP_ACCEPT="application/json",
        )
        self.assertFalse(json.loads(response.content)["ok"])
        self.assertEqual(Payment.objects.count(), 0)


class MahnwesenTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1)
        )
        self.fee = MembershipFee.objects.create(
            member=self.member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2025, 1, 31),
        )
        self.client.force_login(self.admin)

    def test_mahnung_erhoeht_stufe_bis_zwei(self):
        mahnung_erstellen(self.fee, gebuehr=Decimal("5.00"), benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.mahnstufe, 1)
        self.assertIsNotNone(self.fee.letzte_mahnung_am)

        mahnung_erstellen(self.fee, gebuehr=Decimal("5.00"), benutzer=self.admin)
        mahnung_erstellen(self.fee, gebuehr=Decimal("5.00"), benutzer=self.admin)
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.mahnstufe, 2, "Mehr als zwei Mahnstufen sind nicht vorgesehen")
        self.assertEqual(DunningLetter.objects.count(), 3)

    def test_ajax_mahnung_und_uebersicht(self):
        response = self.client.post(
            f"/beitraege/mahnwesen/{self.fee.pk}/mahnung/",
            {"gebuehr": "5.00", "notiz": "Erinnerung"},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["patch"][f"[data-mahnstufe='{self.fee.pk}']"], "1. Mahnung")

        uebersicht = self.client.get("/beitraege/mahnwesen/")
        self.assertContains(uebersicht, "Anna")
        self.assertContains(uebersicht, "Mahnprotokoll")

    def test_mahnbrief_ist_druckbar(self):
        mahnung_erstellen(self.fee, benutzer=self.admin)
        response = self.client.get(f"/beitraege/mahnwesen/{self.fee.pk}/brief/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1. Mahnung")
        self.assertContains(response, "90,00 €")
        self.assertContains(response, "Meier")

    def test_bezahlter_posten_kann_nicht_gemahnt_werden(self):
        zahlung_erfassen(self.fee, betrag=Decimal("90.00"), benutzer=self.admin)
        response = self.client.post(
            f"/beitraege/mahnwesen/{self.fee.pk}/mahnung/", {}, HTTP_ACCEPT="application/json"
        )
        self.assertFalse(json.loads(response.content)["ok"])


class MandatTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1)
        )
        self.client.force_login(self.admin)

    def test_mandat_wird_maskiert_angezeigt(self):
        SepaMandate.objects.create(
            member=self.member, referenz="SCKS-2026-001",
            iban="DE89 3704 0044 0532 0130 00", erteilt_am=date(2026, 1, 5),
        )
        response = self.client.get("/beitraege/mandate/")
        inhalt = response.content.decode()
        self.assertIn("SCKS-2026-001", inhalt)
        self.assertIn("DE89 •••• •••• 3000", inhalt)
        self.assertNotIn("3704 0044 0532", inhalt.replace("•", ""))

    def test_ungueltige_iban_wird_abgelehnt(self):
        response = self.client.post(
            "/beitraege/mandate/neu/",
            {
                "member": self.member.pk,
                "referenz": "SCKS-2026-002",
                "iban": "DE12",
                "erteilt_am": "2026-01-05",
                "status": "aktiv",
                "kontoinhaber": "",
                "notiz": "",
                "widerrufen_am": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SepaMandate.objects.exists())
        self.assertContains(response, "gültige IBAN")

    def test_kategorie_toggle_und_loeschschutz(self):
        kategorie = FeeCategory.objects.create(name="Familie", betrag=Decimal("130.00"))
        self.member.beitragskategorie = kategorie
        self.member.save()
        response = self.client.post(
            f"/beitraege/kategorien/{kategorie.pk}/loeschen/", HTTP_ACCEPT="application/json"
        )
        self.assertFalse(json.loads(response.content)["ok"], "Zugeordnete Kategorie darf nicht gelöscht werden")

        response = self.client.post(
            f"/beitraege/kategorien/{kategorie.pk}/status/", HTTP_ACCEPT="application/json"
        )
        kategorie.refresh_from_db()
        self.assertFalse(kategorie.aktiv)
        self.assertFalse(json.loads(response.content)["checked"])


class MitgliedsKontoTests(TestCase):
    def test_mitglied_sieht_eigene_posten(self):
        user = User.objects.create_user("p1", password="x")
        group, _ = Group.objects.get_or_create(name="mitglied")
        user.groups.add(group)
        member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1), user=user
        )
        MembershipFee.objects.create(
            member=member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )
        self.client.force_login(user)
        response = self.client.get("/mein-beitragskonto/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "90,00 €")
        self.assertContains(response, "Offen")
