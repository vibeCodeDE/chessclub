from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import AuditLog
from dues.crypto import (
    entschluesseln,
    ist_primaer_verschluesselt,
    rotiere_chiffre,
)
from dues.models import SepaMandate


class Command(BaseCommand):
    help = "Rotiert die Verschlüsselung aller SEPA-Mandat-IBANs auf den aktuellen Primärschlüssel."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Führt die Prüfung durch, ohne Änderungen in der Datenbank oder im AuditLog zu speichern.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        rotiert = 0
        aktuell = 0
        fehler = 0

        from django.db import connection

        # Direkte Datenbankabfrage, damit defekte Chiffren nicht bereits beim
        # Laden des Modells via from_db_value() unkontrolliert abbrechen.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, referenz, iban, member_id FROM dues_sepamandate ORDER BY id"
            )
            rows = cursor.fetchall()

        for mandat_id, referenz, raw_iban, member_id in rows:
            if not raw_iban:
                aktuell += 1
                continue

            try:
                # Prüfen, ob Entschlüsselung grundsätzlich möglich ist
                entschluesseln(raw_iban)

                if ist_primaer_verschluesselt(raw_iban):
                    aktuell += 1
                else:
                    neuer_chiffre = rotiere_chiffre(raw_iban)
                    if not dry_run:
                        with transaction.atomic():
                            SepaMandate.objects.filter(pk=mandat_id).update(iban=neuer_chiffre)
                            AuditLog.objects.create(
                                benutzer=None,
                                aktion="IBAN-Schlüssel rotiert",
                                member_id=member_id,
                                text=f"SEPA-Mandat {referenz}: IBAN auf aktuellen Primärschlüssel rotiert.",
                            )
                    rotiert += 1
            except Exception as exc:
                fehler += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"Fehler bei Mandat {referenz} (ID {mandat_id}): {exc}"
                    )
                )

        prefix = "[Dry-Run] " if dry_run else ""
        zusammenfassung = (
            f"{prefix}{rotiert} rotiert, {aktuell} unverändert / bereits aktuell, {fehler} Fehler."
        )

        if fehler > 0:
            self.stderr.write(self.style.WARNING(zusammenfassung))
        else:
            self.stdout.write(self.style.SUCCESS(zusammenfassung))
