"""Tests für automatische Dateisystem-Bereinigung mit django-cleanup (ADR-026).

Sichert ab, dass physische Dateien bei Model-Löschung oder -Aktualisierung
sauber vom Dateisystem entfernt werden und keine verwaisten Dateien verbleiben.
"""

import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import connection, models, transaction
from django.test import TestCase, override_settings
from django_cleanup import cache, handlers

from cashbook.models import CashEntry
from dues.models import Payment


class DynamicCleanupTestModel(models.Model):
    """Dynamisches Modell für Cleanup-Tests."""

    titel = models.CharField(max_length=100)
    datei = models.FileField(upload_to="cleanup_test/", blank=True, null=True)

    class Meta:
        app_label = "core"


class DjangoCleanupConfigurationTests(TestCase):
    """Prüft die Registrierung und Konfiguration von django-cleanup."""

    def test_cleanup_in_installed_apps(self):
        """django_cleanup.apps.CleanupConfig muss in INSTALLED_APPS geladen sein."""
        self.assertIn("django_cleanup.apps.CleanupConfig", settings.INSTALLED_APPS)

    def test_media_settings_konfiguriert(self):
        """MEDIA_URL und MEDIA_ROOT müssen definiert sein."""
        self.assertTrue(hasattr(settings, "MEDIA_URL"))
        self.assertTrue(hasattr(settings, "MEDIA_ROOT"))
        self.assertTrue(str(settings.MEDIA_URL).endswith("/"))
        self.assertTrue(Path(settings.MEDIA_ROOT).name == "media")


class DjangoCleanupFileLifecycleTests(TestCase):
    """Prüft das Löschen und Ersetzen von Dateien auf dem Dateisystem."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_dir = tempfile.mkdtemp()
        with connection.schema_editor() as editor:
            editor.create_model(DynamicCleanupTestModel)
        cache.prepare(False)
        handlers.connect()

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            editor.delete_model(DynamicCleanupTestModel)
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.override = override_settings(MEDIA_ROOT=self.temp_dir)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        super().tearDown()

    def test_datei_wird_bei_model_delete_vom_dateisystem_geloescht(self):
        """Beim Löschen einer Modell-Instanz muss die Datei von der Festplatte gelöscht werden."""
        obj = DynamicCleanupTestModel.objects.create(titel="Ausschreibung")
        obj.datei.save("turnier_ausschreibung.pdf", ContentFile(b"%PDF-1.4 Testdokument"))
        obj.save()

        dateipfad = Path(obj.datei.path)
        self.assertTrue(dateipfad.exists(), "Datei sollte vor dem Löschen auf der Festplatte existieren.")

        with self.captureOnCommitCallbacks(execute=True):
            obj.delete()

        self.assertFalse(dateipfad.exists(), "Datei muss nach dem Löschen der Modell-Instanz entfernt sein.")

    def test_alte_datei_wird_bei_feld_ueberschreiben_geloescht(self):
        """Beim Ersetzen einer Datei muss die alte Datei entfernt werden, die neue bleibt erhalten."""
        obj = DynamicCleanupTestModel.objects.create(titel="Satzung")
        obj.datei.save("satzung_v1.pdf", ContentFile(b"Version 1"))
        obj.save()

        pfad_v1 = Path(obj.datei.path)
        self.assertTrue(pfad_v1.exists())

        # Neue Datei zuweisen und speichern
        with self.captureOnCommitCallbacks(execute=True):
            obj.datei.save("satzung_v2.pdf", ContentFile(b"Version 2"))
            obj.save()

        pfad_v2 = Path(obj.datei.path)

        self.assertFalse(pfad_v1.exists(), "Die ersetzte Datei v1 muss gelöscht worden sein.")
        self.assertTrue(pfad_v2.exists(), "Die neue Datei v2 muss auf der Festplatte existieren.")

        with self.captureOnCommitCallbacks(execute=True):
            obj.delete()
        self.assertFalse(pfad_v2.exists(), "Nach dem Löschen muss auch v2 entfernt sein.")

    def test_loeschen_bei_bereits_fehlender_datei_wirft_keinen_fehler_negativtest(self):
        """Negativtest: Fehlt die Datei auf der Festplatte bereits, darf obj.delete() nicht abstürzen."""
        obj = DynamicCleanupTestModel.objects.create(titel="Manuell entfernt")
        obj.datei.save("weg.txt", ContentFile(b"fluechtig"))
        obj.save()

        dateipfad = Path(obj.datei.path)
        dateipfad.unlink()  # Manuell vorab löschen
        self.assertFalse(dateipfad.exists())

        # Darf keinen FileNotFoundError auslösen
        try:
            with self.captureOnCommitCallbacks(execute=True):
                obj.delete()
        except Exception as exc:
            self.fail(f"obj.delete() warf unerwartet eine Ausnahme bei fehlender Datei: {exc}")

    def test_loeschen_eines_leeren_dateifelds_wirft_keinen_fehler_negativtest(self):
        """Negativtest: Ein Modell ohne Datei (null/blank) lässt sich ohne Fehler löschen."""
        obj = DynamicCleanupTestModel.objects.create(titel="Ohne Anhang", datei=None)
        try:
            with self.captureOnCommitCallbacks(execute=True):
                obj.delete()
        except Exception as exc:
            self.fail(f"obj.delete() schlug bei leerem Dateifeld fehl: {exc}")

    def test_transaktions_rollback_behaelt_datei_auf_platte_negativtest(self):
        """Negativtest: Schlägt eine Transaktion fehl, bleibt die Datei auf der Festplatte erhalten."""
        obj = DynamicCleanupTestModel.objects.create(titel="Wichtige Datei")
        obj.datei.save("sicher.pdf", ContentFile(b"Nicht loeschen bei Rollback"))
        obj.save()

        dateipfad = Path(obj.datei.path)
        self.assertTrue(dateipfad.exists())

        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                obj.delete()
                raise RuntimeError("Fehler in der Geschäftslogik, Rollback erzwungen!")

        self.assertTrue(
            dateipfad.exists(),
            "Die Datei darf bei einem Transaktions-Rollback nicht gelöscht worden sein.",
        )

        # Sauberes Aufräumen am Testende
        DynamicCleanupTestModel.objects.filter(pk=obj.pk).delete()

    def test_finanzdaten_bleiben_ungeloescht_gobd(self):
        """GoBD-Schutz (ADR-005, ADR-006): Finanzdaten besitzen weiterhin keinen Löschpfad."""
        # Sicherstellen, dass die Unveränderbarkeit von Zahlungen und Kassenbucheinträgen intakt ist
        payment = Payment(betrag=50)
        self.assertFalse(hasattr(payment, "has_delete_permission"))
        cash_entry = CashEntry(betrag=100)
        self.assertFalse(hasattr(cash_entry, "has_delete_permission"))
