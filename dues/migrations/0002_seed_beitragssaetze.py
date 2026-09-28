"""Seed: 4 Beitragskategorien mit Sätzen für 2026 und 2027 (PRD M2.1).

Die Beträge sind **Platzhalter** eines fiktiven Vereins und für die echten
Sätze des Vereins vor T8 im Django-Admin zu überschreiben. Aus diesem Grund
läuft die Migration idempotent (``get_or_create``): ein erneuter ``migrate``
oder ein ``migrate dues 0001`` gefolgt von ``0002`` ändert nichts.
"""

from django.db import migrations

CATEGORIES = [
    ("erwachsene", "Erwachsene", [("2026", "90.00"), ("2027", "95.00")]),
    ("jugend", "Jugendliche", [("2026", "45.00"), ("2027", "47.00")]),
    ("familie", "Familie", [("2026", "150.00"), ("2027", "155.00")]),
    ("ermaeßigt", "Ermäßigt", [("2026", "55.00"), ("2027", "57.00")]),
]


def seed(apps, schema_editor):
    FeeCategory = apps.get_model("dues", "FeeCategory")
    FeeAmount = apps.get_model("dues", "FeeAmount")
    for code, bezeichnung, betraege in CATEGORIES:
        kategorie, _ = FeeCategory.objects.get_or_create(
            code=code, defaults={"bezeichnung": bezeichnung, "aktiv": True}
        )
        for jahr, betrag in betraege:
            FeeAmount.objects.get_or_create(
                kategorie=kategorie, jahr=int(jahr), defaults={"betrag": betrag}
            )


def unseed(apps, schema_editor):
    FeeCategory = apps.get_model("dues", "FeeCategory")
    FeeCategory.objects.filter(code__in=[c[0] for c in CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [("dues", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
