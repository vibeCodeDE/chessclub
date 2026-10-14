"""Tests für django-import-export im CashEntryAdmin (PRD S6.1, S6.2, ADR-005, ADR-006, ADR-021)."""

from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase
from tablib import Dataset

from cashbook.admin import CashEntryAdmin
from cashbook.models import CashEntry
from cashbook.resources import CashEntryResource
from core.models import AuditLog


class CashbookImportExportTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser("admin_cash", password="secret_password")
        self.kapitaen_group, _ = Group.objects.get_or_create(name="kapitaen")
        self.mitglied_group, _ = Group.objects.get_or_create(name="mitglied")

        self.kapitaen = User.objects.create_user("kapitaen_cash", password="secret_password")
        self.kapitaen.groups.add(self.kapitaen_group)

        self.mitglied = User.objects.create_user("mitglied_cash", password="secret_password")
        self.mitglied.groups.add(self.mitglied_group)

        self.entry1 = CashEntry.objects.create(
            art=CashEntry.Art.EINNAHME,
            kategorie=CashEntry.Kategorie.BEITRAEGE,
            betrag=Decimal("120.00"),
            datum=date(2026, 3, 1),
            beschreibung="Jahresbeitrag 2026",
            belegnummer="BELEG-001",
            erfasst_von=self.admin_user,
        )
        self.entry2 = CashEntry.objects.create(
            art=CashEntry.Art.AUSGABE,
            kategorie=CashEntry.Kategorie.MATERIAL,
            betrag=Decimal("45.50"),
            datum=date(2026, 3, 15),
            beschreibung="DGT 2010 Schachuhr Ersatz",
            belegnummer="BELEG-002",
            erfasst_von=self.admin_user,
        )

    def test_delete_permission_is_strictly_disabled(self):
        """Negativtest: Finanzbuchungen dürfen im Admin niemals gelöscht werden (ADR-006)."""
        request = RequestFactory().get("/")
        request.user = self.admin_user
        admin = CashEntryAdmin(CashEntry, AdminSite())
        self.assertFalse(admin.has_delete_permission(request))
        self.assertFalse(admin.has_delete_permission(request, self.entry1))

    def test_admin_export_cash_entries_creates_audit_log(self):
        """Admin kann Kassenbuchungen exportieren; AuditLog wird erzeugt."""
        self.client.login(username="admin_cash", password="secret_password")
        AuditLog.objects.all().delete()

        response = self.client.get("/admin/cashbook/cashentry/export/")
        self.assertEqual(response.status_code, 200)

        export_data = {
            "format": "0",
            "resource": "0",
            "cashentryresource_datum": "on",
            "cashentryresource_betrag": "on",
            "cashentryresource_beschreibung": "on",
            "cashentryresource_belegnummer": "on",
        }
        post_response = self.client.post("/admin/cashbook/cashentry/export/", export_data)
        self.assertEqual(post_response.status_code, 200)
        content = post_response.content.decode("utf-8")
        self.assertIn("Jahresbeitrag 2026", content)
        self.assertIn("DGT 2010 Schachuhr Ersatz", content)
        self.assertIn("BELEG-001", content)

        audit = AuditLog.objects.filter(aktion="Kassenbuch exportiert").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.benutzer, self.admin_user)
        self.assertIn("Kassenbuchungen über den Django-Admin exportiert", audit.text)

    def test_cashentry_resource_import_and_erfasst_von(self):
        """Resource setzt beim Import automatisch den Erfasser und validiert Beträge."""
        resource = CashEntryResource()
        dataset = Dataset(
            headers=["datum", "art", "kategorie", "betrag", "beschreibung", "belegnummer"]
        )
        dataset.append(
            ["2026-04-01", "einnahme", "sponsoring", "250.00", "Spende Turnierschach", "SP-2026-01"]
        )

        result = resource.import_data(dataset, dry_run=False, user=self.admin_user)
        self.assertFalse(result.has_errors())
        entry = CashEntry.objects.get(belegnummer="SP-2026-01")
        self.assertEqual(entry.erfasst_von, self.admin_user)
        self.assertEqual(entry.betrag, Decimal("250.00"))

    def test_admin_import_flow_creates_audit_log(self):
        """Web-Workflow für Kassenbuch-Import im Admin erzeugt AuditLog."""
        self.client.login(username="admin_cash", password="secret_password")
        AuditLog.objects.all().delete()

        csv_content = (
            "datum,art,kategorie,betrag,beschreibung,belegnummer\n"
            "2026-05-01,ausgabe,raumkosten,80.00,Miete Vereinsraum Mai,MIETE-05\n"
        )
        file_obj = BytesIO(csv_content.encode("utf-8"))
        file_obj.name = "kasse_import.csv"

        response = self.client.post(
            "/admin/cashbook/cashentry/import/",
            {"import_file": file_obj, "format": "0"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "confirm")

        confirm_response = self.client.post(
            "/admin/cashbook/cashentry/process_import/",
            {
                "import_file_name": response.context["confirm_form"]["import_file_name"].value(),
                "original_file_name": "kasse_import.csv",
                "format": "0",
            },
            follow=True,
        )
        self.assertEqual(confirm_response.status_code, 200)

        self.assertTrue(CashEntry.objects.filter(belegnummer="MIETE-05").exists())
        audit = AuditLog.objects.filter(aktion="Kassenbuch importiert").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.benutzer, self.admin_user)

    def test_non_admin_cannot_access_export_or_import(self):
        """Negativtest: Rollen mitglied und kapitaen erhalten 302/403 auf Kassenbuch-Import/Export."""
        for user in [self.mitglied, self.kapitaen]:
            self.client.login(username=user.username, password="secret_password")

            resp_export = self.client.get("/admin/cashbook/cashentry/export/")
            self.assertIn(resp_export.status_code, [302, 403])

            resp_import = self.client.get("/admin/cashbook/cashentry/import/")
            self.assertIn(resp_import.status_code, [302, 403])

            self.client.logout()

    def test_negative_amount_without_storno_is_rejected(self):
        """Negativtest: Negativer Betrag ohne Storno-Verweis scheitert an der Modellvalidierung."""
        resource = CashEntryResource()
        dataset = Dataset(
            headers=["datum", "art", "kategorie", "betrag", "beschreibung", "belegnummer"]
        )
        dataset.append(
            ["2026-06-01", "ausgabe", "material", "-50.00", "Ungültiger negativer Betrag", "ERR-01"]
        )

        result = resource.import_data(dataset, dry_run=True)
        self.assertTrue(result.has_validation_errors() or result.has_errors())
        self.assertFalse(CashEntry.objects.filter(belegnummer="ERR-01").exists())
