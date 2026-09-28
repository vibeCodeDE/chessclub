"""Stammdaten des Vereins (T10, Grundlage für PRD M2.5).

Der Mahnbrief braucht Absender, Kontakt und Zahlungshinweis. Weil es dafür
noch kein Modell gab, sind die Angaben hier zentral gepflegt statt in den
Templates; T14 (Gruppemail) und T17 (News) lesen denselben Datensatz.

Es ist bewusst **ein** Datensatz: ``Vereinsdaten.aktuell()`` liefert ihn und legt
ihn beim ersten Aufruf an, damit ein frisches Deployment keinen ``DoesNotExist``
in der Briefansicht produziert. Gepflegt wird ausschließlich im Admin.
"""

from django.db import models


class Vereinsdaten(models.Model):
    name = models.CharField("Vereinsname", max_length=100)
    strasse = models.CharField("Straße/Nr.", max_length=200, blank=True)
    plz = models.CharField("PLZ", max_length=10, blank=True)
    ort = models.CharField("Ort", max_length=100, blank=True)
    telefon = models.CharField("Telefon", max_length=50, blank=True)
    email = models.EmailField("E-Mail", blank=True)
    kassierer = models.CharField("Kassierer/in", max_length=100, blank=True)
    zahlungshinweis = models.TextField(
        "Zahlungshinweis",
        blank=True,
        help_text="Textbaustein im Mahnbrief, z. B. die Zahlungswege.",
    )
    zahlungsziel = models.TextField(
        "Verwendungszweck",
        blank=True,
        help_text="Textbaustein im Mahnbrief, z. B. Bankverbindung und Zweck.",
    )

    class Meta:
        verbose_name = "Vereinsdaten"
        verbose_name_plural = "Vereinsdaten"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Genau eine Zeile: ein zweiter Versuch landet auf pk=1 statt eine
        # zweite, konkurrierende Konfiguration anzulegen.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def aktuell(cls):
        """Der eine Datensatz — wird beim ersten Aufruf angelegt."""
        datensatz, _ = cls.objects.get_or_create(
            pk=1, defaults={"name": "Schachverein"}
        )
        return datensatz
