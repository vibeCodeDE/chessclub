import io
from datetime import date

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.roles import ADMIN_GROUP, MITGLIED_GROUP
from dues.models import FeeAmount, FeeCategory, SepaMandate
from members.models import Member
from members.services.import_service import (
    execute_members_import,
    parse_members_csv,
    validate_members_import,
)


class MemberImportServiceTests(TestCase):
    def setUp(self):
        self.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=self.kategorie, jahr=2026, betrag=90)

    def test_parse_csv_semicolon_and_comma(self):
        """CSV-Parser verarbeitet Semikolon- und Komma-getrennte Dateien fehlerfrei."""
        csv_semi = "Vorname;Nachname;E-Mail;Geburtsdatum;Eintrittsdatum;Beitragskategorie\nMax;Mustermann;max@example.com;15.03.1990;01.01.2024;Erwachsene"
        rows = parse_members_csv(csv_semi)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["vorname"], "Max")
        self.assertEqual(rows[0]["nachname"], "Mustermann")
        self.assertEqual(rows[0]["email"], "max@example.com")

        csv_comma = "Vorname,Nachname,E-Mail,Geburtsdatum,Eintrittsdatum,Beitragskategorie\nErika,Musterfrau,erika@example.com,1985-06-20,2023-05-01,Erwachsene"
        rows_comma = parse_members_csv(csv_comma)
        self.assertEqual(len(rows_comma), 1)
        self.assertEqual(rows_comma[0]["vorname"], "Erika")

    def test_validate_and_execute_import_with_sepa(self):
        """Erfolgreicher Import mit Datums-Normalisierung, Kategorie-Zuordnung und SEPA-Mandat."""
        csv_data = (
            "Vorname;Nachname;E-Mail;Geburtsdatum;Eintrittsdatum;Beitragskategorie;IBAN;Kontoinhaber\n"
            "Hans;Schachner;hans@example.com;12.04.1980;01.01.2020;Erwachsene;DE89370400440532013000;Hans Schachner\n"
        )
        rows = parse_members_csv(csv_data)
        validation = validate_members_import(rows)
        self.assertEqual(validation["valid_count"], 1)
        self.assertEqual(validation["error_count"], 0)

        ergebnis = execute_members_import(validation["valid_rows"])
        self.assertEqual(ergebnis["created_members"], 1)
        self.assertEqual(ergebnis["created_mandates"], 1)

        member = Member.objects.get(nachname="Schachner")
        self.assertEqual(member.vorname, "Hans")
        self.assertEqual(member.geburtsdatum, date(1980, 4, 12))
        self.assertEqual(member.eintrittsdatum, date(2020, 1, 1))
        self.assertEqual(member.beitragskategorie, self.kategorie)

        # Prüfen, dass SEPA-Mandat verschlüsselt angelegt wurde
        mandat = SepaMandate.objects.get(member=member)
        self.assertEqual(mandat.iban_kurz, "DE89 •••• •••• 3000")
        self.assertEqual(mandat.kontoinhaber, "Hans Schachner")

    def test_validation_rejects_missing_required_fields_negative_test(self):
        """Negativtest: Zeilen ohne Pflichtfelder werden als fehlerhaft markiert."""
        csv_bad = (
            "Vorname;Nachname;Eintrittsdatum\n"
            ";OhneVorname;01.01.2022\n"
            "OhneNachname;;01.01.2022\n"
            "Ungueltiges;Datum;32.13.2022\n"
        )
        rows = parse_members_csv(csv_bad)
        validation = validate_members_import(rows)
        self.assertEqual(validation["valid_count"], 0)
        self.assertEqual(validation["error_count"], 3)

    def test_management_command_import_members(self):
        """Testet das CLI-Command import_members inkl. Dry-Run."""
        import tempfile

        from django.core.management import call_command

        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tf:
            tf.write("Vorname;Nachname;Eintrittsdatum\nKlaus;Bauer;01.01.2021\n")
            tf_path = tf.name

        try:
            # 1. Dry Run
            out = io.StringIO()
            call_command("import_members", tf_path, "--dry-run", stdout=out)
            self.assertIn("Dry-Run erfolgreich", out.getvalue())
            self.assertFalse(Member.objects.filter(nachname="Bauer").exists())

            # 2. Echter Import
            out_real = io.StringIO()
            call_command("import_members", tf_path, stdout=out_real)
            self.assertIn("Import erfolgreich abgeschlossen", out_real.getvalue())
            self.assertTrue(Member.objects.filter(nachname="Bauer").exists())
        finally:
            import os
            if os.path.exists(tf_path):
                os.remove(tf_path)


class MemberImportViewTests(TestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        self.mitglied_group, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)
        self.admin_user = User.objects.create_user("admin", "admin@example.com", "pass")
        self.admin_user.groups.add(self.admin_group)
        self.mitglied_user = User.objects.create_user("mitglied", "mitg@example.com", "pass")
        self.mitglied_user.groups.add(self.mitglied_group)

    def test_muster_csv_download(self):
        """Admin kann die Vorlage-CSV herunterladen."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("core:club_setup_import_muster"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertContains(response, "Vorname;Nachname;E-Mail")

    def test_upload_and_preview_dry_run(self):
        """Admin lädt CSV hoch und sieht eine Vorschau (Dry-Run, noch kein DB-Eintrag)."""
        self.client.force_login(self.admin_user)
        csv_content = b"Vorname;Nachname;E-Mail;Eintrittsdatum\nAnna;Test;anna@example.com;01.01.2023\n"
        uploaded_file = SimpleUploadedFile("mitglieder.csv", csv_content, content_type="text/csv")

        url = reverse("core:club_setup_members_import")
        response = self.client.post(url, {"csv_file": uploaded_file, "aktion": "pruefen"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anna")
        self.assertContains(response, "Test")
        # In der DB darf noch kein Mitglied angelegt worden sein
        self.assertFalse(Member.objects.filter(nachname="Test").exists())

    def test_non_admin_forbidden_negative_test(self):
        """Negativtest: Mitglied erhält 403 auf Import-Routen."""
        self.client.force_login(self.mitglied_user)
        response = self.client.get(reverse("core:club_setup_members_import"))
        self.assertEqual(response.status_code, 403)
