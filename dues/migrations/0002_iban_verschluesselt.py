"""IBAN verschlüsselt speichern (ADR-010).

Der Bestand wird hier einmalig umgeschrieben: Spalte verbreitern, Maske
befüllen, Klartext in Chiffretext umwandeln, dann erst das Feld tauschen.
"""

import re

from django.db import migrations, models

import dues.crypto
import dues.fields

IBAN_MUSTER = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{10,30}$")


def _maske(iban):
    if not iban or len(iban) <= 8:
        return iban or ""
    return f"{iban[:4]} •••• •••• {iban[-4:]}"


def verschluessel_bestand(apps, schema_editor):
    SepaMandate = apps.get_model("dues", "SepaMandate")
    for mandat in SepaMandate.objects.all().iterator():
        klartext = re.sub(r"\s+", "", mandat.iban or "").upper()
        if klartext and not IBAN_MUSTER.match(klartext):
            # Ungültige Altwerte nicht verschlüsseln, sondern unverändert lassen –
            # sie werden in der Oberfläche ohnehin zur Korrektur angezeigt.
            continue
        SepaMandate.objects.filter(pk=mandat.pk).update(
            iban=dues.crypto.verschluesseln(klartext),
            iban_kurz=_maske(klartext),
        )


def entschluessel_bestand(apps, schema_editor):
    SepaMandate = apps.get_model("dues", "SepaMandate")
    for mandat in SepaMandate.objects.all().iterator():
        if not dues.crypto.ist_chiffre(mandat.iban):
            continue
        klartext = dues.crypto.entschluesseln(mandat.iban)
        SepaMandate.objects.filter(pk=mandat.pk).update(iban=klartext)


class Migration(migrations.Migration):
    dependencies = [("dues", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="sepamandate",
            name="iban_kurz",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="Nicht umkehrbare Kurzform für Listen, aus der IBAN abgeleitet.",
                max_length=40,
                verbose_name="IBAN (maskiert)",
            ),
        ),
        migrations.AlterField(
            model_name="sepamandate",
            name="iban",
            field=models.CharField(max_length=255, verbose_name="IBAN"),
        ),
        migrations.RunPython(verschluessel_bestand, entschluessel_bestand),
        migrations.AlterField(
            model_name="sepamandate",
            name="iban",
            field=dues.fields.VerschluesseltesIbanField(
                help_text=(
                    "Wird verschlüsselt gespeichert (ADR-010) und in Listen nur "
                    "maskiert angezeigt. Ein Einzug findet ausschließlich bankseitig statt."
                ),
                verbose_name="IBAN",
            ),
        ),
    ]
