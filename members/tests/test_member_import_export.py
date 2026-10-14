"""Tests für django-import-export im MemberAdmin (PRD M1.5, S1.7, N1.5, ADR-021)."""

from datetime import date
from io import BytesIO

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase
from tablib import Dataset

from core.models import AuditLog
from dues.models import FeeCategory
from members.admin import MemberAdmin
from members.models import Member, MemberStatusChange
from members.resources import MemberResource


class MemberImportExportTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser("admin_user", password="secret_password")
        self.kapitaen_group, _ = Group.objects.get_or_create(name="kapitaen")
        self.mitglied_group, _ = Group.objects.get_or_create(name="mitglied")

        self.kapitaen = User.objects.create_user("kapitaen_user", password="secret_password")
        self.kapitaen.groups.add(self.kapitaen_group)

        self.mitglied = User.objects.create_user("mitglied_user", password="secret_password")
        self.mitglied.groups.add(self.mitglied_group)

        self.kategorie = FeeCategory.objects.create(name="Erwachsene")
        self.member1 = Member.objects.create(
            vorname="Emanuel",
            nachname="Lasker",
            eintrittsdatum=date(2020, 1, 1),
            status=Member.Status.AKTIV,
            beitragskategorie=self.kategorie,
            email="lasker@example.org",
        )
        self.member2 = Member.objects.create(
            vorname="Jose",
            nachname="Capablanca",
            eintrittsdatum=date(2021, 5, 10),
            status=Member.Status.PASSIV,
            email="capa@example.org",
        )

    def test_delete_permission_remains_strictly_disabled(self):
        """Negativtest: Mitglieder dürfen über den Admin niemals gelöscht werden."""
        request = RequestFactory().get("/")
        request.user = self.admin_user
        admin = MemberAdmin(Member, AdminSite())
        self.assertFalse(admin.has_delete_permission(request))
        self.assertFalse(admin.has_delete_permission(request, self.member1))

    def test_admin_export_members_creates_audit_log(self):
        """Admin kann Mitglieder exportieren; AuditLog wird erzeugt (DSGVO N1.5)."""
        self.client.login(username="admin_user", password="secret_password")
        AuditLog.objects.all().delete()

        response = self.client.get("/admin/members/member/export/")
        self.assertEqual(response.status_code, 200)

        # POST export action (Format 0 ist CSV, resource 0 ist MemberResource, Felder auswählen)
        export_data = {
            "format": "0",
            "resource": "0",
            "memberresource_nachname": "on",
            "memberresource_vorname": "on",
            "memberresource_status": "on",
            "memberresource_beitragskategorie": "on",
        }
        post_response = self.client.post("/admin/members/member/export/", export_data)
        self.assertEqual(post_response.status_code, 200)
        content = post_response.content.decode("utf-8")
        self.assertIn("Lasker", content)
        self.assertIn("Capablanca", content)
        self.assertIn("Erwachsene", content)

        # AuditLog verifizieren
        audit = AuditLog.objects.filter(aktion="Mitgliederliste exportiert").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.benutzer, self.admin_user)
        self.assertIn("Mitglieder über den Django-Admin exportiert", audit.text)

    def test_member_resource_export_and_import_cycle(self):
        """Resource exportiert und importiert fehlerfrei mit FK-Auflösung."""
        resource = MemberResource()
        dataset = resource.export()
        self.assertEqual(len(dataset), 2)
        self.assertIn("Lasker", dataset["nachname"])

        # Neuer Datensatz per Dataset importieren
        dataset_neu = Dataset(
            headers=[
                "id",
                "nachname",
                "vorname",
                "status",
                "beitragskategorie",
                "eintrittsdatum",
                "email",
            ]
        )
        dataset_neu.append(
            ["", "Alekhine", "Alexander", "aktiv", "Erwachsene", "2023-01-01", "alex@example.org"]
        )

        result = resource.import_data(dataset_neu, dry_run=False, user=self.admin_user)
        self.assertFalse(result.has_errors())
        self.assertTrue(Member.objects.filter(nachname="Alekhine").exists())
        alekhine = Member.objects.get(nachname="Alekhine")
        self.assertEqual(alekhine.beitragskategorie, self.kategorie)

    def test_admin_import_flow_and_audit_log(self):
        """Web-Workflow für Import im Admin setzt Statusänderungshistorie und AuditLog."""
        self.client.login(username="admin_user", password="secret_password")
        AuditLog.objects.all().delete()

        # CSV-Datei simulieren
        csv_content = (
            "id,nachname,vorname,status,beitragskategorie,eintrittsdatum,email\n"
            f"{self.member1.pk},Lasker,Emanuel,ausgetreten,,2020-01-01,lasker@example.org\n"
        )
        file_obj = BytesIO(csv_content.encode("utf-8"))
        file_obj.name = "import.csv"

        # 1. Vorschau anfordern
        response = self.client.post(
            "/admin/members/member/import/",
            {"import_file": file_obj, "format": "0"},
            follow=True,
        )
        # Austrittsdatum fehlt im Input, Modell-Validierung muss Fehler melden!
        # Negativtest: clean_model_instances fängt fehlendes austrittsdatum ab
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            "Bei Status „ausgetreten“ ist ein Austrittsdatum erforderlich." in response.content.decode("utf-8")
            or "Errors" in response.content.decode("utf-8")
        )

        # Jetzt mit gültigem Austrittsdatum
        csv_valid = (
            "id,nachname,vorname,status,beitragskategorie,eintrittsdatum,austrittsdatum,email\n"
            f"{self.member1.pk},Lasker,Emanuel,ausgetreten,,2020-01-01,2026-10-01,lasker@example.org\n"
        )
        file_valid = BytesIO(csv_valid.encode("utf-8"))
        file_valid.name = "import.csv"

        response2 = self.client.post(
            "/admin/members/member/import/",
            {"import_file": file_valid, "format": "0"},
        )
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, "confirm")

        # Bestätigungs-POST ausführen
        confirm_response = self.client.post(
            "/admin/members/member/process_import/",
            {
                "import_file_name": response2.context["confirm_form"]["import_file_name"].value(),
                "original_file_name": "import.csv",
                "format": "0",
            },
            follow=True,
        )
        self.assertEqual(confirm_response.status_code, 200)

        self.member1.refresh_from_db()
        self.assertEqual(self.member1.status, Member.Status.AUSGETRETEN)

        # StatusChangeHistorie prüfen
        history = MemberStatusChange.objects.filter(member=self.member1).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.geaendert_von, self.admin_user)

        # AuditLog für Import prüfen
        audit = AuditLog.objects.filter(aktion="Mitglieder importiert").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.benutzer, self.admin_user)

    def test_non_admin_cannot_access_export_or_import(self):
        """Negativtest: Rollen mitglied und kapitaen erhalten keinen Zugriff auf Import/Export."""
        for user in [self.mitglied, self.kapitaen]:
            self.client.login(username=user.username, password="secret_password")

            resp_export = self.client.get("/admin/members/member/export/")
            self.assertIn(resp_export.status_code, [302, 403])

            resp_import = self.client.get("/admin/members/member/import/")
            self.assertIn(resp_import.status_code, [302, 403])

            self.client.logout()

    def test_invalid_import_data_rejected_by_clean_model_instances(self):
        """Negativtest: Datensätze mit Datumsinkonsistenzen werden abgewiesen."""
        resource = MemberResource()
        dataset = Dataset(
            headers=["nachname", "vorname", "status", "eintrittsdatum", "austrittsdatum"]
        )
        # Austrittsdatum vor Eintrittsdatum
        dataset.append(["Botvinnik", "Mikhail", "ausgetreten", "2025-01-01", "2020-01-01"])

        result = resource.import_data(dataset, dry_run=True)
        self.assertTrue(result.has_validation_errors() or result.has_errors())
        self.assertFalse(Member.objects.filter(nachname="Botvinnik").exists())
