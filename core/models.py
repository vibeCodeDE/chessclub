from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLogQuerySet(models.QuerySet):
    def aufbewahrungsfrist_abgelaufen(self, tage=365):
        """Findet Einträge, deren 12-monatige Aufbewahrungsfrist abgelaufen ist (PRD N1.5)."""
        grenze = timezone.now() - timedelta(days=tage)
        return self.filter(zeitpunkt__lt=grenze)

    def aelter_als(self, tage=365):
        return self.aufbewahrungsfrist_abgelaufen(tage=tage)


class AuditLog(models.Model):
    """Nachvollziehbare Protokollierung sicherheitsrelevanter Aktionen.

    T4 schreibt den Eintrag bei der Freigabe eines Änderungswunschs;
    T5 ergänzt Signale für Stammdaten-Änderungen (Wer, Was, Wann, Alt/Neu
    in ``feld``/``alt_wert``/``neu_wert``) und Anmelde-Ereignisse.
    T12 protokolliert Detailansichts-Zugriffe und Datenauskunfts-Exporte (N1.5).
    """

    objects = AuditLogQuerySet.as_manager()

    zeitpunkt = models.DateTimeField("Zeitpunkt", auto_now_add=True)
    benutzer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Benutzer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    aktion = models.CharField("Aktion", max_length=100)
    text = models.TextField("Details", blank=True)
    member = models.ForeignKey(
        "members.Member",
        verbose_name="Mitglied",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    feld = models.CharField("Feld", max_length=30, blank=True)
    # TextField (nicht CharField mit max_length): Mitgliedsfelder erlauben bis
    # zu 254 Zeichen (E-Mail); ein zu kurzer Audit-Wert würde den Save sonst
    # auf Postgres mit „value too long" komplett fehlschlagen lassen.
    alt_wert = models.TextField("Alter Wert", blank=True)
    neu_wert = models.TextField("Neuer Wert", blank=True)

    class Meta:
        ordering = ["-zeitpunkt"]

    def __str__(self):
        return f"{self.zeitpunkt:%Y-%m-%d %H:%M} · {self.aktion}"

    def anzeige_wert(self, wert=None):
        """FK-Werte als Objekt beschriften – eine Datenbank-ID ist kein Lesewert.

        `kategorie_namen` setzt die Changelist des Audits einmal je Seitenaufruf
        (siehe ``AuditLogAdmin.get_results``); ohne sie greift derEinzelfall, was
        in der Detailansicht genau eine Abfrage ist.
        """
        from dues.models import FeeCategory

        if wert is None:
            wert = self.neu_wert
        if self.feld != "beitragskategorie" or not wert:
            return wert
        try:
            schluessel = int(wert)
        except (TypeError, ValueError):
            return wert
        namen = getattr(self, "kategorie_namen", None)
        if namen is None:
            kategorien = FeeCategory.objects.all()
            return next((k for k in kategorien if k.pk == schluessel), wert)
        return namen.get(schluessel, wert)

    @property
    def aufbewahrungsfrist_abgelaufen(self):
        """Gibt zurück, ob die 12-monatige Aufbewahrungsfrist abgelaufen ist (PRD N1.5)."""
        if not self.zeitpunkt:
            return False
        return self.zeitpunkt < (timezone.now() - timedelta(days=365))


class TwoFactorDevice(models.Model):
    """TOTP-Gerät eines Vorstands-Kontos (PRD N1.6)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Benutzer",
        on_delete=models.CASCADE,
        related_name="zwei_faktor",
    )
    secret = models.CharField("Geheime Zeichenfolge", max_length=64)
    bestaetigt = models.BooleanField("Bestätigt", default=False)
    erstellt_am = models.DateTimeField("Erstellt am", auto_now_add=True)
    letzte_nutzung = models.DateTimeField("Zuletzt genutzt", null=True, blank=True)

    class Meta:
        verbose_name = "Zwei-Faktor-Gerät"
        verbose_name_plural = "Zwei-Faktor-Geräte"

    def __str__(self):
        return f"2FA für {self.user.get_username()}"
