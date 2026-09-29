"""Spielbetrieb: Mannschaften, Ligaspiele, Aufstellungen (PRD M4)."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from members.models import Member


class Team(models.Model):
    """Mannschaft eines Vereins, z. B. 1. Mannschaft (PRD M4.1)."""

    class Altersklasse(models.TextChoices):
        ERWACHSENE = "erwachsene", "Erwachsene"
        JUGEND = "jugend", "Jugend"
        SENIOREN = "senioren", "Senioren"

    name = models.CharField("Mannschaft", max_length=100, unique=True)
    liga = models.CharField("Liga / Staffel", max_length=120, blank=True)
    altersklasse = models.CharField(
        "Altersklasse", max_length=20, choices=Altersklasse.choices, default=Altersklasse.ERWACHSENE
    )
    brettanzahl = models.PositiveSmallIntegerField("Bretter", default=8)
    kapitaen = models.ForeignKey(
        Member,
        verbose_name="Mannschaftsführer:in",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="kapitaen_von",
    )
    aktiv = models.BooleanField("Aktiv", default=True)

    class Meta:
        verbose_name = "Mannschaft"
        verbose_name_plural = "Mannschaften"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def naechstes_spiel(self):
        from django.utils import timezone

        return (
            self.matches.filter(datum__gte=timezone.localdate())
            .exclude(status=LeagueMatch.Status.GESPIELT)
            .order_by("datum", "uhrzeit")
            .first()
        )

    @property
    def bilanz(self):
        spiele = self.matches.filter(status=LeagueMatch.Status.GESPIELT)
        sieg = remis = niederlage = 0
        for match in spiele:
            eigen, gegner = match.brettpunkte
            if eigen > gegner:
                sieg += 1
            elif eigen == gegner:
                remis += 1
            else:
                niederlage += 1
        return {"siege": sieg, "remis": remis, "niederlagen": niederlage, "spiele": spiele.count()}


class LeagueMatch(models.Model):
    """Ein Ligaspiel mit Termin, Gegner und Ergebnissen (PRD M4.2/M4.4)."""

    class Status(models.TextChoices):
        GEPLANT = "geplant", "Geplant"
        AUFGESTELLT = "aufgestellt", "Aufstellung gemeldet"
        GESPIELT = "gespielt", "Gespielt"

    team = models.ForeignKey(
        Team, verbose_name="Mannschaft", on_delete=models.CASCADE, related_name="matches"
    )
    datum = models.DateField("Datum")
    uhrzeit = models.TimeField("Uhrzeit", null=True, blank=True)
    gegner = models.CharField("Gegner", max_length=120)
    heimspiel = models.BooleanField("Heimspiel", default=True)
    ort = models.CharField("Spielort", max_length=150, blank=True)
    runde = models.CharField("Runde / Spieltag", max_length=60, blank=True)
    brettanzahl = models.PositiveSmallIntegerField("Bretter", default=8)
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.GEPLANT)
    ergebnis_eigen = models.DecimalField(
        "Brettpunkte eigen", max_digits=4, decimal_places=1, null=True, blank=True
    )
    ergebnis_gegner = models.DecimalField(
        "Brettpunkte Gegner", max_digits=4, decimal_places=1, null=True, blank=True
    )
    bemerkung = models.CharField("Bemerkung", max_length=250, blank=True)
    erstellt_am = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        verbose_name = "Ligaspiel"
        verbose_name_plural = "Ligaspiele"
        ordering = ["datum", "uhrzeit", "gegner"]

    def __str__(self):
        return f"{self.team} – {self.gegner} ({self.datum:%d.%m.%Y})"

    @property
    def brettpunkte(self):
        """Summe der Bretter – automatisch, sobald Ergebnisse erfasst sind (M4.4)."""
        eigen = Decimal("0.0")
        gegner = Decimal("0.0")
        hat_ergebnis = False
        for eintrag in self.aufstellung.all():
            punkte = eintrag.punkte
            if punkte is None:
                continue
            hat_ergebnis = True
            eigen += punkte
            gegner += Decimal("1.0") - punkte
        return (eigen, gegner) if hat_ergebnis else (None, None)

    @property
    def brettpunkte_anzeige(self):
        eigen, gegner = self.brettpunkte
        if eigen is None:
            return "–"
        return f"{eigen:.1f} : {gegner:.1f}"

    @property
    def mannschaftspunkte(self):
        eigen, gegner = self.brettpunkte
        if eigen is None:
            return None
        if eigen > gegner:
            return 2
        if eigen == gegner:
            return 1
        return 0

    @property
    def ergebnis_klasse(self):
        punkte = self.mannschaftspunkte
        if punkte is None:
            return "offen"
        return {2: "sieg", 1: "remis", 0: "niederlage"}[punkte]

    def status_aktualisieren(self, commit=True):
        if self.aufstellung.exists() and self.status == self.Status.GEPLANT:
            self.status = self.Status.AUFGESTELLT
        eigen, gegner = self.brettpunkte
        if eigen is not None:
            self.ergebnis_eigen = eigen
            self.ergebnis_gegner = gegner
        if commit:
            self.save(update_fields=["status", "ergebnis_eigen", "ergebnis_gegner"])
        return self.status

    def clean(self):
        super().clean()
        if self.brettanzahl and not 1 <= self.brettanzahl <= 20:
            raise ValidationError({"brettanzahl": "Bitte zwischen 1 und 20 Brettern angeben."})


class LineupEntry(models.Model):
    """Aufstellung: ein Brett eines Ligaspiels (PRD M4.3)."""

    class Ergebnis(models.TextChoices):
        OFFEN = "", "Offen"
        SIEG = "1", "Sieg (1)"
        REMIS = "0.5", "Remis (½)"
        NIEDERLAGE = "0", "Niederlage (0)"

    PUNKTE = {"1": Decimal("1.0"), "0.5": Decimal("0.5"), "0": Decimal("0.0")}

    match = models.ForeignKey(
        LeagueMatch, verbose_name="Ligaspiel", on_delete=models.CASCADE, related_name="aufstellung"
    )
    brett = models.PositiveSmallIntegerField("Brett")
    member = models.ForeignKey(
        Member,
        verbose_name="Spieler:in",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lineups",
    )
    ersatz_name = models.CharField(
        "Ersatzspieler:in (extern)", max_length=120, blank=True,
        help_text="Nur ausfüllen, wenn die Person kein Mitglied ist.",
    )
    gegner_name = models.CharField("Gegner am Brett", max_length=120, blank=True)
    ergebnis = models.CharField(
        "Ergebnis", max_length=5, choices=Ergebnis.choices, blank=True, default=""
    )

    class Meta:
        verbose_name = "Aufstellungseintrag"
        verbose_name_plural = "Aufstellung"
        ordering = ["match", "brett"]
        constraints = [
            models.UniqueConstraint(fields=["match", "brett"], name="unique_brett_pro_spiel"),
        ]

    def __str__(self):
        return f"{self.match} · Brett {self.brett}"

    @property
    def spieler_name(self):
        if self.member:
            return str(self.member)
        return self.ersatz_name or "– nicht benannt –"

    @property
    def punkte(self):
        return self.PUNKTE.get(self.ergebnis)

    @property
    def ergebnis_anzeige(self):
        return self.get_ergebnis_display() or "offen"
