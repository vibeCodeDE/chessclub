"""Kassenbuch: Einnahmen/Ausgaben (PRD S6.1)."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone


class CashEntry(models.Model):
    """Eine Buchung im Kassenbuch – Einnahme oder Ausgabe."""

    class Art(models.TextChoices):
        EINNAHME = "einnahme", "Einnahme"
        AUSGABE = "ausgabe", "Ausgabe"

    class Kategorie(models.TextChoices):
        BEITRAEGE = "beitraege", "Mitgliedsbeiträge"
        STARTGELD = "startgeld", "Startgelder"
        SPONSORING = "sponsoring", "Sponsoring / Spenden"
        TURNIERKOSTEN = "turnierkosten", "Turnierkosten"
        MATERIAL = "material", "Material & Ausstattung"
        RAUMKOSTEN = "raumkosten", "Raumkosten"
        VERBANDSABGABEN = "verbandsabgaben", "Verbandsabgaben"
        EHRUNGEN = "ehrungen", "Ehrungen & Jugendarbeit"
        SONSTIGES = "sonstiges", "Sonstiges"

    art = models.CharField("Art", max_length=20, choices=Art.choices)
    kategorie = models.CharField("Kategorie", max_length=30, choices=Kategorie.choices)
    betrag = models.DecimalField("Betrag (€)", max_digits=9, decimal_places=2)
    datum = models.DateField("Buchungsdatum", default=timezone.localdate)
    beschreibung = models.CharField("Beschreibung", max_length=250)
    belegnummer = models.CharField("Beleg-Nr.", max_length=60, blank=True)
    storno_von = models.OneToOneField(
        "self",
        verbose_name="Storno von",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="storno_buchung",
    )
    erfasst_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Erfasst von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cash_entries",
    )
    erstellt_am = models.DateTimeField("Erfasst am", auto_now_add=True)

    class Meta:
        verbose_name = "Kassenbuchung"
        verbose_name_plural = "Kassenbuchungen"
        ordering = ["-datum", "-erstellt_am"]

    def __str__(self):
        return f"{self.get_art_display()}: {self.beschreibung} ({self.betrag} €)"

    def clean(self):
        super().clean()
        if self.storno_von_id:
            if self.betrag is not None and self.betrag >= 0:
                raise ValidationError({"betrag": "Eine Storno-Gegenbuchung muss einen negativen Betrag haben."})
        else:
            if self.betrag is not None and self.betrag <= 0:
                raise ValidationError({"betrag": "Der Betrag muss größer als 0 sein."})

    @property
    def vorzeichen_betrag(self):
        return self.betrag if self.art == self.Art.EINNAHME else -self.betrag

    @property
    def ist_einnahme(self):
        return self.art == self.Art.EINNAHME

    @property
    def ist_storno(self):
        return self.storno_von_id is not None

    @property
    def ist_storniert(self):
        return CashEntry.objects.filter(storno_von_id=self.pk).exists() if self.pk else False

    @property
    def kategorie_label(self):
        return self.get_kategorie_display()


@transaction.atomic
def storniere_kassenbuchung(buchung, *, benutzer=None, grund="", datum=None):
    """Erzeugt eine Storno-Gegenbuchung statt hartem Löschen (GoBD-konform)."""
    from core.models import AuditLog

    if buchung.ist_storno:
        raise ValidationError("Eine Storno-Gegenbuchung kann nicht erneut storniert werden.")
    if buchung.ist_storniert:
        raise ValidationError("Diese Kassenbuchung wurde bereits storniert.")
    if not grund or not str(grund).strip():
        raise ValidationError("Für ein Storno ist eine Begründung erforderlich.")
    if benutzer is None:
        raise ValidationError("Für ein Storno ist ein Erfasser (Benutzer) erforderlich.")

    grund_clean = str(grund).strip()
    betrag = Decimal(str(buchung.betrag)).quantize(Decimal("0.01"))
    zusatz = f" ({grund_clean})"
    beschreibung = f"Storno zu #{buchung.pk}: {buchung.beschreibung}{zusatz}"[:250]
    beleg = f"STORNO-{buchung.belegnummer or buchung.pk}"[:60]
    gegenbuchung = CashEntry.objects.create(
        art=buchung.art,
        kategorie=buchung.kategorie,
        betrag=-betrag,
        datum=datum or buchung.datum,
        beschreibung=beschreibung,
        belegnummer=beleg,
        storno_von=buchung,
        erfasst_von=benutzer,
    )
    AuditLog.objects.create(
        benutzer=benutzer,
        aktion="Kassenbuchung storniert",
        text=f"Storno zu Buchung #{buchung.pk}: {buchung.beschreibung} ({betrag:.2f} €){zusatz}",
    )
    return gegenbuchung


def jahresabschluss(jahr):
    """Summen je Kategorie und Gesamtsaldo für den Kassenbericht (S6.2)."""
    buchungen = CashEntry.objects.filter(datum__year=jahr)
    einnahmen = buchungen.filter(art=CashEntry.Art.EINNAHME).aggregate(s=Sum("betrag"))["s"] or Decimal("0.00")
    ausgaben = buchungen.filter(art=CashEntry.Art.AUSGABE).aggregate(s=Sum("betrag"))["s"] or Decimal("0.00")
    kategorien = {}
    for zeile in buchungen.values("kategorie", "art").annotate(s=Sum("betrag")).order_by("kategorie"):
        eintrag = kategorien.setdefault(
            zeile["kategorie"],
            {"label": CashEntry.Kategorie(zeile["kategorie"]).label, "einnahmen": Decimal("0.00"), "ausgaben": Decimal("0.00")},
        )
        eintrag["einnahmen" if zeile["art"] == CashEntry.Art.EINNAHME else "ausgaben"] += zeile["s"]
    for eintrag in kategorien.values():
        eintrag["saldo"] = eintrag["einnahmen"] - eintrag["ausgaben"]
    return {
        "jahr": jahr,
        "einnahmen": einnahmen,
        "ausgaben": ausgaben,
        "saldo": einnahmen - ausgaben,
        "anzahl": buchungen.count(),
        "kategorien": kategorien,
    }
