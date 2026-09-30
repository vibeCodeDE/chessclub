"""Anonymisiert ausgetretene Mitglieder nach Ablauf der Aufbewahrungsfrist (PRD N1.3).

Aufruf:
    python manage.py anonymize_former_members --dry-run
    python manage.py anonymize_former_members --frist-tage 730
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.dsgvo import (
    ANONYMISIERUNGS_FRIST_TAGE,
    anonymisiere_member,
    anonymisierungs_kandidaten,
)


class Command(BaseCommand):
    help = "Entfernt Kontaktdaten ausgetretener Mitglieder nach der konfigurierten Frist."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Nur anzeigen, welche Mitglieder anonymisiert würden.",
        )
        parser.add_argument(
            "--frist-tage",
            type=int,
            default=ANONYMISIERUNGS_FRIST_TAGE,
            help=f"Aufbewahrungsfrist in Tagen nach Austritt (Standard: {ANONYMISIERUNGS_FRIST_TAGE}).",
        )

    def handle(self, *args, **options):
        kandidaten = list(anonymisierungs_kandidaten(frist_tage=options["frist_tage"]))
        trocken = options["dry_run"]

        if not kandidaten:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Keine Kandidat:innen – alle Ausgetretenen innerhalb der letzten "
                    f"{options['frist_tage']} Tage sind unberührt."
                )
            )
            return

        for member in kandidaten:
            hinweis = (
                f"{member.nachname}, {member.vorname} (ID {member.pk}, "
                f"Austritt {member.austrittsdatum:%d.%m.%Y})"
            )
            if trocken:
                self.stdout.write(f"[dry-run] würde anonymisieren: {hinweis}")
                continue
            anonymisiere_member(member)
            self.stdout.write(self.style.WARNING(f"anonymisiert: {hinweis}"))

        if trocken:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(kandidaten)} Kandidat:in(nen) gefunden – nichts geändert (--dry-run)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{len(kandidaten)} Mitglied(er) anonymisiert am {timezone.localdate():%d.%m.%Y}."
                )
            )
