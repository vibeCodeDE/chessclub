import datetime
from django.db import migrations


def populate_default_season(apps, schema_editor):
    Season = apps.get_model("teams", "Season")
    Team = apps.get_model("teams", "Team")

    default_season = Season.objects.filter(ist_aktiv=True).first()
    if not default_season:
        default_season, _ = Season.objects.get_or_create(
            name="2025/2026",
            defaults={
                "slug": "2025-2026",
                "startdatum": datetime.date(2025, 8, 1),
                "enddatum": datetime.date(2026, 7, 31),
                "status": "aktiv",
                "ist_aktiv": True,
                "notizen": "Automatisch bei Migration initialisierte Standardsaison.",
            },
        )

    Team.objects.filter(saison__isnull=True).update(saison=default_season)


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0003_season_alter_team_name_team_saison"),
    ]

    operations = [
        migrations.RunPython(populate_default_season, reverse_func),
    ]
