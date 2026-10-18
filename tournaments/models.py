"""Turniere, Anmeldungen, Paarungen und Wertung (PRD M3)."""

from django.db import models
from django.utils import timezone


class Tournament(models.Model):
    """Turnier mit Anmeldefrist, Format und Status (PRD M3.1)."""

    class Format(models.TextChoices):
        SCHWEIZER = "schweizer", "Schweizer System"
        RUNDEN = "runden", "Rundenturnier (jeder gegen jeden)"
        KO = "ko", "K.-o.-System"
        RAPID = "rapid", "Rapidturnier"
        BLITZ = "blitz", "Blitzturnier"

    class Status(models.TextChoices):
        ENTWURF = "entwurf", "Entwurf"
        ANMELDUNG = "anmeldung", "Anmeldung offen"
        LAUFEND = "laufend", "Läuft"
        BEENDET = "beendet", "Beendet"

    name = models.CharField("Turniername", max_length=150)
    saison = models.ForeignKey(
        "teams.Season",
        verbose_name="Saison",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="turniere",
    )
    datum = models.DateField("Turnierdatum")
    anmeldeschluss = models.DateField("Anmeldeschluss", null=True, blank=True)
    ort = models.CharField("Spielort", max_length=150, blank=True)
    format = models.CharField("Format", max_length=20, choices=Format.choices, default=Format.SCHWEIZER)
    runden_anzahl = models.PositiveSmallIntegerField("Runden", default=5)
    startgeld = models.DecimalField("Startgeld (€)", max_digits=6, decimal_places=2, default=0)
    beschreibung = models.TextField("Ausschreibung", blank=True)
    oeffentlich = models.BooleanField(
        "Öffentlich sichtbar", default=True, help_text="Anmeldung auch für Gäste ohne Konto."
    )
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.ENTWURF)
    erstellt_am = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        verbose_name = "Turnier"
        verbose_name_plural = "Turniere"
        ordering = ["-datum"]

    def __str__(self):
        return self.name

    @property
    def teilnehmer_anzahl(self):
        return self.teilnehmer.count()

    @property
    def offene_startgelder(self):
        return self.teilnehmer.filter(startgeld_bezahlt=False).count()

    @property
    def anmeldung_offen(self):
        if self.status not in {self.Status.ANMELDUNG, self.Status.ENTWURF}:
            return False
        if self.anmeldeschluss and self.anmeldeschluss < timezone.localdate():
            return False
        return True

    @property
    def runden_count(self):
        return self.runden.count()

    @property
    def ist_laufend(self):
        return self.status == self.Status.LAUFEND


class Participant(models.Model):
    """Teilnehmer:in eines Turniers – Mitglied oder Gast (PRD M3.2)."""

    tournament = models.ForeignKey(
        Tournament, verbose_name="Turnier", on_delete=models.CASCADE, related_name="teilnehmer"
    )
    member = models.ForeignKey(
        "members.Member",
        verbose_name="Mitglied",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="turnierteilnahmen",
    )
    name = models.CharField("Name", max_length=150)
    verein = models.CharField("Verein", max_length=150, blank=True)
    twz = models.PositiveIntegerField("DWZ / TWZ", null=True, blank=True)
    geburtsjahr = models.PositiveSmallIntegerField("Geburtsjahr", null=True, blank=True)
    email = models.EmailField("E-Mail", blank=True)
    startgeld_bezahlt = models.BooleanField("Startgeld bezahlt", default=False)
    angemeldet_am = models.DateTimeField("Angemeldet am", auto_now_add=True)
    notiz = models.CharField("Notiz", max_length=200, blank=True)

    class Meta:
        verbose_name = "Teilnehmer:in"
        verbose_name_plural = "Teilnehmer:innen"
        ordering = ["-twz", "name"]
        constraints = [
            models.UniqueConstraint(fields=["tournament", "name"], name="unique_teilnehmer_pro_turnier"),
        ]

    def __str__(self):
        return f"{self.name} ({self.tournament.name})"

    @property
    def punkte(self):
        """Turnierpunkte inklusive Bye."""
        summe = 0.0
        for paarung in self.paarungen_als_weiss.all() | self.paarungen_als_schwarz.all():
            summe += paarung.punkte_fuer(self)
        return round(summe, 1)

    @property
    def buchholz(self):
        """Buchholz: Summe der Punkte aller Gegner (S3.4)."""
        gegner = []
        for paarung in self.paarungen_als_weiss.all() | self.paarungen_als_schwarz.all():
            andere = paarung.gegner_von(self)
            if andere:
                gegner.append(andere.punkte)
        return round(sum(gegner), 1)

    @property
    def ist_mitglied(self):
        return self.member_id is not None


class TournamentRound(models.Model):
    """Eine Runde innerhalb eines Turniers (PRD M3.3)."""

    tournament = models.ForeignKey(
        Tournament, verbose_name="Turnier", on_delete=models.CASCADE, related_name="runden"
    )
    nummer = models.PositiveSmallIntegerField("Runde")
    freigabe_am = models.DateTimeField("Freigegeben am", null=True, blank=True)

    class Meta:
        verbose_name = "Runde"
        verbose_name_plural = "Runden"
        ordering = ["nummer"]
        constraints = [
            models.UniqueConstraint(fields=["tournament", "nummer"], name="unique_runde_pro_turnier"),
        ]

    def __str__(self):
        return f"{self.tournament.name} · Runde {self.nummer}"

    @property
    def offene_partien(self):
        return self.paarungen.filter(ergebnis="").count()


class Pairing(models.Model):
    """Paarung eines Brettes in einer Runde (PRD S3.4)."""

    class Ergebnis(models.TextChoices):
        OFFEN = "", "Offen"
        WEISS = "1-0", "Weiß gewinnt"
        SCHWARZ = "0-1", "Schwarz gewinnt"
        REMIS = "remis", "Remis"
        BYE = "bye", "Kampflos (Bye)"

    runde = models.ForeignKey(
        TournamentRound, verbose_name="Runde", on_delete=models.CASCADE, related_name="paarungen"
    )
    brett = models.PositiveSmallIntegerField("Brett")
    weiss = models.ForeignKey(
        Participant,
        verbose_name="Weiß",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="paarungen_als_weiss",
    )
    schwarz = models.ForeignKey(
        Participant,
        verbose_name="Schwarz",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="paarungen_als_schwarz",
    )
    ergebnis = models.CharField("Ergebnis", max_length=10, choices=Ergebnis.choices, blank=True, default="")

    class Meta:
        verbose_name = "Paarung"
        verbose_name_plural = "Paarungen"
        ordering = ["runde__nummer", "brett"]
        constraints = [
            models.UniqueConstraint(fields=["runde", "brett"], name="unique_brett_pro_runde"),
        ]

    def __str__(self):
        return f"Brett {self.brett}: {self.weiss} – {self.schwarz}"

    def gegner_von(self, participant):
        if participant.pk == (self.weiss_id or 0):
            return self.schwarz
        if participant.pk == (self.schwarz_id or 0):
            return self.weiss
        return None

    def punkte_fuer(self, participant):
        if self.ergebnis == self.Ergebnis.BYE and participant.pk == (self.weiss_id or 0):
            return 1.0
        if self.ergebnis == self.Ergebnis.WEISS:
            return 1.0 if participant.pk == (self.weiss_id or 0) else 0.0
        if self.ergebnis == self.Ergebnis.SCHWARZ:
            return 1.0 if participant.pk == (self.schwarz_id or 0) else 0.0
        if self.ergebnis == self.Ergebnis.REMIS:
            return 0.5
        return 0.0

    @property
    def ergebnis_anzeige(self):
        return self.get_ergebnis_display() or "offen"


def teilnehmer_stand(tournament):
    """Aktueller Zwischenstand inkl. Rang nach Punkten, Buchholz und TWZ."""
    teilnehmer = list(tournament.teilnehmer.all())
    for p in teilnehmer:
        p.aktuelle_punkte = p.punkte
        p.aktuelle_buchholz = p.buchholz
    teilnehmer.sort(key=lambda p: (-p.aktuelle_punkte, -p.aktuelle_buchholz, -(p.twz or 0), p.name))
    for rang, p in enumerate(teilnehmer, start=1):
        p.rang = rang
    return teilnehmer
