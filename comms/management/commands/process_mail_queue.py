from django.core.management.base import BaseCommand

from comms.services import process_mail_queue_batch


class Command(BaseCommand):
    help = "Verarbeitet ausstehende E-Mails aus der Warteschlange blockweise."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Maximale Anzahl an E-Mails, die in diesem Durchlauf verarbeitet werden (Standard: 50).",
        )
        parser.add_argument(
            "--max-retries",
            type=int,
            default=3,
            help="Maximale Anzahl an Sendeversuchen, bevor eine Mail als fehlgeschlagen markiert wird (Standard: 3).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simuliert den Versand, ohne E-Mails über SMTP zu verschicken oder Status zu ändern.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        max_retries = options["max_retries"]
        dry_run = options["dry_run"]

        ergebnis = process_mail_queue_batch(
            limit=limit,
            max_retries=max_retries,
            dry_run=dry_run,
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"[Dry-Run] {ergebnis['dry_run']} E-Mail(s) würden verarbeitet werden ({ergebnis['verbleibend']} verbleibend)."
                )
            )
        else:
            ausgabe = (
                f"{ergebnis['gesendet']} versendet, "
                f"{ergebnis['fehlgeschlagen']} fehlgeschlagen, "
                f"{ergebnis['verbleibend']} verbleibend."
            )
            if ergebnis["fehlgeschlagen"] > 0:
                self.stderr.write(self.style.WARNING(ausgabe))
            else:
                self.stdout.write(self.style.SUCCESS(ausgabe))
