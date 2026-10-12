# Generated manually for T30 / S7.4 / ADR-019

from django.db import migrations, models


def erstelle_standard_einstellungen(apps, schema_editor):
    ModuleSettings = apps.get_model("core", "ModuleSettings")
    ModuleSettings.objects.get_or_create(
        pk=1,
        defaults={
            "spielbetrieb_aktiv": True,
            "turniere_aktiv": True,
            "kassenbuch_aktiv": True,
            "nachrichten_aktiv": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_twofactordevice_letzter_zeitschritt"),
    ]

    operations = [
        migrations.CreateModel(
            name="ModuleSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "spielbetrieb_aktiv",
                    models.BooleanField(
                        default=True,
                        help_text="Aktiviert Mannschaften, Ligaspiele, Aufstellungen und Ligatabellen.",
                        verbose_name="Spielbetrieb & Mannschaften",
                    ),
                ),
                (
                    "turniere_aktiv",
                    models.BooleanField(
                        default=True,
                        help_text="Aktiviert Turnierverwaltung, öffentliche Anmeldung und Schweizer System.",
                        verbose_name="Turniere",
                    ),
                ),
                (
                    "kassenbuch_aktiv",
                    models.BooleanField(
                        default=True,
                        help_text="Aktiviert das allgemeine Einnahmen-/Ausgaben-Kassenbuch.",
                        verbose_name="Kassenbuch",
                    ),
                ),
                (
                    "nachrichten_aktiv",
                    models.BooleanField(
                        default=True,
                        help_text="Aktiviert Ankündigungen, News-Archiv und E-Mail-Rundschreiben.",
                        verbose_name="Kommunikation & News",
                    ),
                ),
            ],
            options={
                "verbose_name": "Modul-Einstellung",
                "verbose_name_plural": "Modul-Einstellungen",
            },
        ),
        migrations.RunPython(
            erstelle_standard_einstellungen,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
