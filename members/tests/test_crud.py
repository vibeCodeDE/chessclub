"""CRUD-Flows für Mitglieder inkl. optimistischem Statuswechsel."""

import json
from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase

from core.models import AuditLog
from dues.models import FeeCategory
from members.models import Member


def make_admin(username="vorstand"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


def form_daten(**aenderungen):
    daten = {
        "vorname": "Nele",
        "nachname": "Neumann",
        "geburtsdatum": "2001-05-04",
        "strasse": "Ringstraße 7",
        "plz": "37073",
        "ort": "Musterstadt",
        "email": "nele@example.org",
        "telefon": "0551 987654",
        "eintrittsdatum": "2026-09-01",
        "status": "aktiv",
        "austrittsdatum": "",
        "beitragskategorie": "",
        "email_opt_in": "on",
    }
    daten.update(aenderungen)
    return daten


class MemberCrudTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.force_login(self.admin)
        self.kategorie = FeeCategory.objects.create(name="Erwachsene")

    def test_create_legt_mitglied_und_audit_eintrag_an(self):
        response = self.client.post("/mitglieder/neu/", form_daten())
        self.assertEqual(response.status_code, 302)
        member = Member.objects.get(nachname="Neumann")
        self.assertEqual(member.ort, "Musterstadt")
        self.assertTrue(
            AuditLog.objects.filter(aktion="Mitglied angelegt", member=member).exists()
        )

    def test_create_validiert_pflichtfelder(self):
        response = self.client.post("/mitglieder/neu/", form_daten(nachname=""))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Member.objects.exists())
        self.assertContains(response, "Dieses Feld ist zwingend erforderlich")

    def test_update_speichert_und_protokolliert_aenderung(self):
        member = Member.objects.create(
            vorname="Nele", nachname="Neumann", eintrittsdatum=date(2026, 9, 1)
        )
        response = self.client.post(
            f"/mitglieder/{member.pk}/bearbeiten/", form_daten(ort="Neustadt")
        )
        self.assertRedirects(response, f"/mitglieder/{member.pk}/")
        member.refresh_from_db()
        self.assertEqual(member.ort, "Neustadt")
        self.assertTrue(
            AuditLog.objects.filter(aktion="Stammdaten geändert", feld="ort", member=member).exists()
        )

    def test_ajax_create_antwortet_json(self):
        response = self.client.post(
            "/mitglieder/neu/", form_daten(), HTTP_ACCEPT="application/json"
        )
        self.assertEqual(response.status_code, 200)
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertIn("/mitglieder/", daten["redirect"])

    def test_statuswechsel_per_ajax(self):
        member = Member.objects.create(
            vorname="Nele", nachname="Neumann", eintrittsdatum=date(2026, 9, 1)
        )
        response = self.client.post(
            f"/mitglieder/{member.pk}/status/",
            {"status": "passiv"},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.PASSIV)
        self.assertEqual(daten["patch"][f"[data-status-text='{member.pk}']"], "Passiv")

    def test_austritt_setzt_status_ohne_loeschen(self):
        member = Member.objects.create(
            vorname="Nele", nachname="Neumann", eintrittsdatum=date(2020, 1, 1)
        )
        response = self.client.post(f"/mitglieder/{member.pk}/austritt/")
        self.assertEqual(response.status_code, 302)
        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.AUSGETRETEN)
        self.assertEqual(member.austrittsdatum, date.today())
        self.assertTrue(member.status_history.exists())

    def test_austritt_ohne_datum_wird_abgelehnt(self):
        member = Member.objects.create(
            vorname="Nele", nachname="Neumann", eintrittsdatum=date(2026, 9, 1)
        )
        response = self.client.post(
            f"/mitglieder/{member.pk}/status/",
            {"status": "passiv", "austrittsdatum": "2026-01-01"},
            HTTP_ACCEPT="application/json",
        )
        self.assertFalse(json.loads(response.content)["ok"])

    def test_filter_nach_kategorie_und_status(self):
        kategorie = self.kategorie
        Member.objects.create(
            vorname="A", nachname="Aktiv", eintrittsdatum=date(2026, 1, 1),
            status=Member.Status.AKTIV, beitragskategorie=kategorie,
        )
        Member.objects.create(
            vorname="B", nachname="Passiv", eintrittsdatum=date(2026, 1, 1),
            status=Member.Status.PASSIV,
        )
        response = self.client.get("/mitglieder/", {"status": "passiv"})
        self.assertContains(response, "Passiv")
        self.assertNotContains(response, "Aktiv,")
        response = self.client.get("/mitglieder/", {"kategorie": str(kategorie.pk)})
        self.assertContains(response, "Aktiv")

    def test_csv_export_enthaelt_kategorie(self):
        Member.objects.create(
            vorname="Nele", nachname="Neumann", eintrittsdatum=date(2026, 9, 1),
            beitragskategorie=self.kategorie,
        )
        response = self.client.get("/mitglieder/export.csv")
        inhalt = response.content.decode("utf-8-sig")
        self.assertIn("Beitragskategorie", inhalt)
        self.assertIn("Erwachsene", inhalt)
