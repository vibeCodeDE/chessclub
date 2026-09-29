"""Kassenbuch: Buchungen, Jahresabschluss und Export."""

import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from cashbook.models import CashEntry, jahresabschluss


def make_admin(username="kassenwart"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


class KassenbuchTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.force_login(self.admin)

    def test_buchung_anlegen_mit_erfasser(self):
        response = self.client.post(
            "/kasse/neu/",
            {"art": "ausgabe", "kategorie": "material", "betrag": "49.90",
             "datum": "2026-05-04", "beschreibung": "Turnieruhren", "belegnummer": "B-12"},
        )
        self.assertRedirects(response, "/kasse/")
        buchung = CashEntry.objects.get()
        self.assertEqual(buchung.erfasst_von, self.admin)
        self.assertEqual(buchung.betrag, Decimal("49.90"))
        self.assertFalse(buchung.ist_einnahme)

    def test_negativer_betrag_wird_abgelehnt(self):
        response = self.client.post(
            "/kasse/neu/",
            {"art": "einnahme", "kategorie": "sponsoring", "betrag": "-5",
             "datum": "2026-05-04", "beschreibung": "Fehler", "belegnummer": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CashEntry.objects.exists())

    def test_jahresabschluss_summiert_korrekt(self):
        CashEntry.objects.create(art="einnahme", kategorie="beitraege", betrag="1000.00", datum=date(2026, 2, 1), beschreibung="Beiträge")
        CashEntry.objects.create(art="einnahme", kategorie="sponsoring", betrag="250.50", datum=date(2026, 3, 1), beschreibung="Spende")
        CashEntry.objects.create(art="ausgabe", kategorie="raumkosten", betrag="480.00", datum=date(2026, 4, 1), beschreibung="Miete")
        CashEntry.objects.create(art="ausgabe", kategorie="material", betrag="120.00", datum=date(2025, 4, 1), beschreibung="Vorjahr")

        abschluss = jahresabschluss(2026)
        self.assertEqual(abschluss["einnahmen"], Decimal("1250.50"))
        self.assertEqual(abschluss["ausgaben"], Decimal("480.00"))
        self.assertEqual(abschluss["saldo"], Decimal("770.50"))
        self.assertEqual(abschluss["anzahl"], 3)
        self.assertEqual(abschluss["kategorien"]["beitraege"]["saldo"], Decimal("1000.00"))

    def test_jahresfilter_und_export(self):
        CashEntry.objects.create(art="einnahme", kategorie="startgeld", betrag="96.00", datum=date(2026, 6, 1), beschreibung="Blitzturnier")
        CashEntry.objects.create(art="ausgabe", kategorie="material", betrag="10.00", datum=date(2025, 6, 1), beschreibung="Alt")

        response = self.client.get("/kasse/?jahr=2026")
        self.assertContains(response, "Blitzturnier")
        self.assertNotContains(response, "Alt")

        response = self.client.get("/kasse/export.csv?jahr=2026")
        inhalt = response.content.decode("utf-8-sig")
        self.assertIn("Blitzturnier", inhalt)
        self.assertNotIn("Alt", inhalt)
        self.assertIn("Saldo", inhalt)

    def test_loeschen_ueber_ajax(self):
        buchung = CashEntry.objects.create(
            art="einnahme", kategorie="sonstiges", betrag="5.00",
            datum=date(2026, 7, 1), beschreibung="Kleinigkeit",
        )
        response = self.client.post(
            f"/kasse/{buchung.pk}/loeschen/", HTTP_ACCEPT="application/json"
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertFalse(CashEntry.objects.filter(pk=buchung.pk).exists())

    def test_abschlussseite_zeigt_kategorien(self):
        CashEntry.objects.create(art="einnahme", kategorie="beitraege", betrag="900.00", datum=date(2026, 1, 5), beschreibung="Beiträge")
        response = self.client.get("/kasse/jahresabschluss/?jahr=2026")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mitgliedsbeiträge")
        self.assertContains(response, "900,00 €")
