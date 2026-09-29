"""Beitragswesen: Kategorien, Beitragsläufe, SEPA-Mandate, Zahlungen (PRD M2)."""

import re
from decimal import Decimal
from functools import reduce

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from .fields import VerschluesseltesIbanField

IBAN_MUSTER = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{10,30}$")


def normalize_iban(value):
    return re.sub(r"\s+", "", (value or "")).upper()


def format_iban(iban):
    """IBAN in Vierergruppen – lesbar, aber ohne Klartext-Anzeige in Listen."""
    return " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))


def mask_iban(iban):
    """DSGVO-freundliche Kurzanzeige: DE89 •••• •••• 1234."""
    if not iban:
        return ""
    if len(iban) <= 8:
        return iban
    return f"{iban[:4]} •••• •••• {iban[-4:]}"


class FeeCategory(models.Model):
    """Beitragssatz, z. B. Erwachsene, Jugendliche, Familie (PRD M2.1)."""

    name = models.CharField("Bezeichnung", max_length=100, unique=True)
    beschreibung = models.CharField("Beschreibung", max_length=200, blank=True)
    betrag = models.DecimalField("Jahresbeitrag (€)", max_digits=8, decimal_places=2)
    aktiv = models.BooleanField("Aktiv", default=True)

    class Meta:
        verbose_name = "Beitragskategorie"
        verbose_name_plural = "Beitragskategorien"
        ordering = ["betrag", "name"]

    def __str__(self):
        return f"{self.name} ({self.betrag} €)"

    @property
    def mitglieder_anzahl(self):
        return self.mitglieder.exclude(status="ausgetreten").count()


class SepaMandate(models.Model):
    """SEPA-Lastschriftmandat je Mitglied (PRD M2.3).

    Der Verein zieht bankseitig manuell ein – hier wird nur das Mandat
    verwaltet, es gibt bewusst keine Banking-API-Anbindung.
    """

    class Status(models.TextChoices):
        AKTIV = "aktiv", "Aktiv"
        WIDERRUFEN = "widerrufen", "Widerrufen"

    member = models.OneToOneField(
        "members.Member",
        verbose_name="Mitglied",
        on_delete=models.CASCADE,
        related_name="sepa_mandat",
    )
    referenz = models.CharField("Mandatsreferenz", max_length=50, unique=True)
    iban = VerschluesseltesIbanField(
        "IBAN",
        help_text=(
            "Wird verschlüsselt gespeichert (ADR-010) und in Listen nur "
            "maskiert angezeigt. Ein Einzug findet ausschließlich bankseitig statt."
        ),
    )
    iban_kurz = models.CharField(
        "IBAN (maskiert)",
        max_length=40,
        blank=True,
        editable=False,
        help_text="Nicht umkehrbare Kurzform für Listen, aus der IBAN abgeleitet.",
    )
    kontoinhaber = models.CharField("Kontoinhaber:in", max_length=150, blank=True)
    erteilt_am = models.DateField("Erteilt am")
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.AKTIV)
    widerrufen_am = models.DateField("Widerrufen am", null=True, blank=True)
    notiz = models.CharField("Notiz", max_length=200, blank=True)

    class Meta:
        verbose_name = "SEPA-Mandat"
        verbose_name_plural = "SEPA-Mandate"
        ordering = ["member__nachname", "member__vorname"]

    def __str__(self):
        return f"{self.member} · {self.referenz}"

    @property
    def iban_formatiert(self):
        return format_iban(self.iban)

    def clean(self):
        super().clean()
        iban = normalize_iban(self.iban)
        if iban and not IBAN_MUSTER.match(iban):
            raise ValidationError({"iban": "Bitte eine gültige IBAN angeben (z. B. DE89 3704 0044 0532 0130 00)."})
        if self.status == self.Status.WIDERRUFEN and not self.widerrufen_am:
            raise ValidationError({"widerrufen_am": "Bei widerrufenem Mandat ist das Datum erforderlich."})

    def save(self, *args, **kwargs):
        self.iban = normalize_iban(self.iban)
        # Die Maske im Klartext mitführen: Listen und Auswertungen müssen dafür
        # nichts entschlüsseln (und nichts zusätzlich laden).
        self.iban_kurz = mask_iban(self.iban)
        super().save(*args, **kwargs)


class MembershipFee(models.Model):
    """Beitragsposten eines Mitglieds für ein Jahr (PRD M2.2)."""

    class Status(models.TextChoices):
        OFFEN = "offen", "Offen"
        TEILWEISE = "teilweise", "Teilweise bezahlt"
        BEZAHLT = "bezahlt", "Bezahlt"
        ERLASSEN = "erlassen", "Erlassen"

    member = models.ForeignKey(
        "members.Member",
        verbose_name="Mitglied",
        on_delete=models.CASCADE,
        related_name="fees",
    )
    jahr = models.PositiveSmallIntegerField("Beitragsjahr")
    kategorie_name = models.CharField("Kategorie", max_length=100)
    betrag = models.DecimalField("Betrag (€)", max_digits=8, decimal_places=2)
    faellig_am = models.DateField("Fällig am")
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.OFFEN)
    mahnstufe = models.PositiveSmallIntegerField("Mahnstufe", default=0)
    letzte_mahnung_am = models.DateField("Letzte Mahnung am", null=True, blank=True)
    erstellt_am = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        verbose_name = "Beitragsposten"
        verbose_name_plural = "Beitragsposten"
        ordering = ["-jahr", "member__nachname", "member__vorname"]
        constraints = [
            models.UniqueConstraint(fields=["member", "jahr"], name="unique_beitrag_pro_jahr"),
        ]

    def __str__(self):
        return f"{self.member} · {self.jahr}"

    @property
    def bezahlter_betrag(self):
        return self.zahlungen.aggregate(s=Sum("betrag"))["s"] or Decimal("0.00")

    @property
    def offener_betrag(self):
        if self.status in {self.Status.BEZAHLT, self.Status.ERLASSEN}:
            return Decimal("0.00")
        return max(self.betrag - self.bezahlter_betrag, Decimal("0.00"))

    @property
    def ist_offen(self):
        return self.offener_betrag > Decimal("0.00")

    @property
    def fortschritt_prozent(self):
        if self.betrag <= 0:
            return 100
        return min(int(round(float(self.bezahlter_betrag) / float(self.betrag) * 100)), 100)

    def status_aktualisieren(self, commit=True):
        bezahlt = self.bezahlter_betrag
        if self.status != self.Status.ERLASSEN:
            if bezahlt >= self.betrag:
                self.status = self.Status.BEZAHLT
            elif bezahlt > 0:
                self.status = self.Status.TEILWEISE
            else:
                self.status = self.Status.OFFEN
            if self.status == self.Status.BEZAHLT:
                self.mahnstufe = 0
        if commit:
            self.save(update_fields=["status", "mahnstufe"])
        return self.status


class Payment(models.Model):
    """Zahlungseingang – manuell gebucht (PRD M2.3b), kein Bank-API-Zugriff."""

    class Art(models.TextChoices):
        SEPA = "sepa", "SEPA-Einzug"
        UEBERWEISUNG = "ueberweisung", "Überweisung"
        BAR = "bar", "Barzahlung"

    fee = models.ForeignKey(
        MembershipFee,
        verbose_name="Beitragsposten",
        on_delete=models.CASCADE,
        related_name="zahlungen",
    )
    betrag = models.DecimalField("Betrag (€)", max_digits=8, decimal_places=2)
    datum = models.DateField("Zahlungsdatum", default=timezone.localdate)
    art = models.CharField("Zahlungsart", max_length=20, choices=Art.choices, default=Art.UEBERWEISUNG)
    notiz = models.CharField("Notiz", max_length=200, blank=True)
    erfasst_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Erfasst von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments",
    )
    erstellt_am = models.DateTimeField("Erfasst am", auto_now_add=True)

    class Meta:
        verbose_name = "Zahlung"
        verbose_name_plural = "Zahlungen"
        ordering = ["-datum", "-erstellt_am"]

    def __str__(self):
        return f"{self.betrag} € · {self.fee.member} ({self.get_art_display()})"

    def clean(self):
        super().clean()
        if self.betrag is not None and self.betrag <= 0:
            raise ValidationError({"betrag": "Der Betrag muss größer als 0 sein."})


class DunningLetter(models.Model):
    """Versandte Mahnung (PRD M2.4) – Nachweis und Druckvorlage."""

    fee = models.ForeignKey(
        MembershipFee,
        verbose_name="Beitragsposten",
        on_delete=models.CASCADE,
        related_name="mahnungen",
    )
    stufe = models.PositiveSmallIntegerField("Mahnstufe")
    datum = models.DateField("Mahndatum", default=timezone.localdate)
    gebuehr = models.DecimalField("Mahngebühr (€)", max_digits=6, decimal_places=2, default=Decimal("0.00"))
    notiz = models.CharField("Notiz", max_length=200, blank=True)
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Erstellt von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dunning_letters",
    )
    erstellt_am = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        verbose_name = "Mahnung"
        verbose_name_plural = "Mahnungen"
        ordering = ["-datum", "-stufe"]

    def __str__(self):
        return f"{self.stufe}. Mahnung · {self.fee.member} ({self.fee.jahr})"


def jahres_uebersicht(jahr):
    """Kennzahlen eines Beitragsjahres für Dashboard und Kassenbericht."""
    posten = MembershipFee.objects.filter(jahr=jahr)
    summen = posten.aggregate(
        soll=Sum("betrag"),
    )
    bezahlt = Payment.objects.filter(fee__jahr=jahr).aggregate(s=Sum("betrag"))["s"] or Decimal("0.00")
    soll = summen["soll"] or Decimal("0.00")
    return {
        "jahr": jahr,
        "soll": soll,
        "bezahlt": bezahlt,
        "offen": max(soll - bezahlt, Decimal("0.00")),
        "anzahl": posten.count(),
        "offene_anzahl": reduce(
            lambda acc, fee: acc + (1 if fee.ist_offen else 0),
            posten.prefetch_related("zahlungen"),
            0,
        ),
    }
