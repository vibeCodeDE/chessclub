"""Management-Command zum Importieren von Mitgliedern aus einer CSV-Datei (PRD S1.7, ADR-020).

Aufruf:
    python manage.py import_members /pfad/zu/mitglieder.csv
    python manage.py import_members /pfad/zu/mitglieder.csv --dry-run
"""

import os

from django.core.management.base import BaseCommand, CommandError

from members.services.import_service import (
    execute_members_import,
    parse_members_csv,
    validate_members_import,
)


class Command(BaseCommand):
    help = "Importiert echte Mitgliederdaten aus einer CSV-Datei in die Datenbank."

    def add_arguments(self, parser):
        parser.add_argument("csv_pfad", type=str, help="Pfad zur CSV-Datei")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Prüft die Datei und zeigt Vorschau, ohne Daten in der DB zu speichern.",
        )

    def handle(self, *args, **options):
        csv_pfad = options["csv_pfad"]
        dry_run = options["dry_run"]

        if not os.path.isfile(csv_pfad):
            raise CommandError(f"Datei '{csv_pfad}' wurde nicht gefunden.")

        self.stdout.write(f"Lese Datei '{csv_pfad}' ein...")
        with open(csv_pfad, "rb") as f:
            rows = parse_members_csv(f)

        if not rows:
            self.stdout.write(self.style.WARNING("Keine Datenzeilen in der CSV-Datei gefunden."))
            return

        self.stdout.write(f"{len(rows)} Zeilen gefunden. Validiere...")
        validation = validate_members_import(rows)

        self.stdout.write(f"Gültige Datensätze: {validation['valid_count']}")
        self.stdout.write(f"Fehlerhafte Datensätze: {validation['error_count']}")
        self.stdout.write(f"Warnungen: {validation['warning_count']}")

        for w in validation["warnings"]:
            self.stdout.write(self.style.WARNING(f"  [WARNUNG] {w}"))

        if validation["invalid_rows"]:
            self.stdout.write(self.style.ERROR("Gefundene Fehler:"))
            for err in validation["invalid_rows"]:
                self.stdout.write(
                    self.style.ERROR(f"  Zeile {err['zeile']}: {', '.join(err['fehler'])}")
                )

        if validation["valid_count"] == 0:
            raise CommandError("Abbruch: Keine gültigen Datensätze vorhanden.")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-Run erfolgreich: Keine Daten verändert."))
            return

        ergebnis = execute_members_import(validation["valid_rows"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Import erfolgreich abgeschlossen: {ergebnis['created_members']} Mitglieder "
                f"und {ergebnis['created_mandates']} SEPA-Mandate angelegt."
            )
        )
