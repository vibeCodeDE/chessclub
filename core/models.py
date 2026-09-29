from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Nachvollziehbare Protokollierung sicherheitsrelevanter Aktionen.

    T4 schreibt den Eintrag bei der Freigabe eines Änderungswunschs;
    T5 ergänzt Signale für Stammdaten-Änderungen (Wer, Was, Wann, Alt/Neu
    in ``feld``/``alt_wert``/``neu_wert``) und Login-Ereignisse.
    """

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
    alt_wert = models.CharField("Alter Wert", max_length=200, blank=True)
    neu_wert = models.CharField("Neuer Wert", max_length=200, blank=True)

    class Meta:
        ordering = ["-zeitpunkt"]

    def __str__(self):
        return f"{self.zeitpunkt:%Y-%m-%d %H:%M} · {self.aktion}"


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
