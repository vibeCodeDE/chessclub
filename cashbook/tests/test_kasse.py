"""Kassenbuch: Buchungen, Jahresabschluss und Export."""

import json
from datetime import date
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase

from cashbook.admin import CashEntryAdmin
from cashbook.models import CashEntry, jahresabschluss, storniere_kassenbuchung
from core.models import AuditLog


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

    def test_loeschen_ueber_ajax_storniert_statt_hard_delete(self):
        buchung = CashEntry.objects.create(
            art="einnahme", kategorie="sonstiges", betrag="5.00",
            datum=date(2026, 7, 1), beschreibung="Kleinigkeit",
        )
        response = self.client.post(
            f"/kasse/{buchung.pk}/loeschen/", HTTP_ACCEPT="application/json"
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertTrue(CashEntry.objects.filter(pk=buchung.pk).exists(), "Originalbuchung darf nicht gelöscht werden")
        self.assertTrue(buchung.ist_storniert)
        gegen = CashEntry.objects.get(storno_von=buchung)
        self.assertEqual(gegen.betrag, Decimal("-5.00"))
        self.assertTrue(gegen.ist_storno)
        self.assertEqual(jahresabschluss(2026)["saldo"], Decimal("0.00"))
        self.assertTrue(AuditLog.objects.filter(aktion="Kassenbuchung storniert").exists())

    def test_storno_route_und_doppelstorno_schutz(self):
        buchung = CashEntry.objects.create(
            art="ausgabe", kategorie="material", betrag="35.00",
            datum=date(2026, 8, 1), beschreibung="Figurensatz", belegnummer="B-99",
        )
        response = self.client.post(f"/kasse/{buchung.pk}/storno/", {"grund": "Fehlbuchung"})
        self.assertRedirects(response, "/kasse/")
        gegen = CashEntry.objects.get(storno_von=buchung)
        self.assertEqual(gegen.betrag, Decimal("-35.00"))
        self.assertIn("Fehlbuchung", gegen.beschreibung)
        self.assertEqual(jahresabschluss(2026)["ausgaben"], Decimal("0.00"))

        # Zweites Storno auf dieselbe Buchung wird abgewiesen
        zweiter = self.client.post(
            f"/kasse/{buchung.pk}/storno/", HTTP_ACCEPT="application/json"
        )
        self.assertFalse(json.loads(zweiter.content)["ok"])
        # Storno auf die Gegenbuchung selbst wird ebenfalls abgewiesen
        with self.assertRaises(ValidationError):
            storniere_kassenbuchung(gegen, benutzer=self.admin)

    def test_stornierte_buchung_nicht_bearbeitbar(self):
        buchung = CashEntry.objects.create(
            art="einnahme", kategorie="sponsoring", betrag="100.00",
            datum=date(2026, 6, 1), beschreibung="Spende",
        )
        storniere_kassenbuchung(buchung, benutzer=self.admin)
        response = self.client.post(
            f"/kasse/{buchung.pk}/bearbeiten/",
            {"art": "einnahme", "kategorie": "sponsoring", "betrag": "200.00",
             "datum": "2026-06-01", "beschreibung": "Manipuliert"},
            HTTP_ACCEPT="application/json",
        )
        self.assertFalse(json.loads(response.content)["ok"])
        buchung.refresh_from_db()
        self.assertEqual(buchung.betrag, Decimal("100.00"))

    def test_buchung_bearbeiten_und_filter(self):
        buchung = CashEntry.objects.create(
            art="ausgabe", kategorie="material", betrag="20.00",
            datum=date(2026, 5, 1), beschreibung="Alt",
        )
        get_resp = self.client.get(f"/kasse/{buchung.pk}/bearbeiten/")
        self.assertEqual(get_resp.status_code, 200)
        post_resp = self.client.post(
            f"/kasse/{buchung.pk}/bearbeiten/",
            {"art": "ausgabe", "kategorie": "material", "betrag": "25.00",
             "datum": "2026-05-01", "beschreibung": "Neu", "belegnummer": "B-1"},
        )
        self.assertRedirects(post_resp, "/kasse/")
        buchung.refresh_from_db()
        self.assertEqual(buchung.betrag, Decimal("25.00"))

        liste = self.client.get("/kasse/?jahr=2026&art=ausgabe&kategorie=material")
        self.assertContains(liste, "Neu")

    def test_admin_verbietet_loeschen_und_nicht_admin_403(self):
        buchung = CashEntry.objects.create(
            art="einnahme", kategorie="sonstiges", betrag="10.00",
            datum=date(2026, 5, 1), beschreibung="Test",
        )
        model_admin = CashEntryAdmin(CashEntry, AdminSite())
        self.assertFalse(model_admin.has_delete_permission(None, buchung))

        mitglied = User.objects.create_user("m1", password="x")
        g, _ = Group.objects.get_or_create(name="mitglied")
        mitglied.groups.add(g)
        self.client.force_login(mitglied)
        self.assertEqual(self.client.post(f"/kasse/{buchung.pk}/storno/").status_code, 403)
        self.assertFalse(buchung.ist_storniert)

    def test_abschlussseite_zeigt_kategorien(self):
        CashEntry.objects.create(art="einnahme", kategorie="beitraege", betrag="900.00", datum=date(2026, 1, 5), beschreibung="Beiträge")
        response = self.client.get("/kasse/jahresabschluss/?jahr=2026")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mitgliedsbeiträge")
        self.assertContains(response, "900,00 €")
