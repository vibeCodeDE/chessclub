from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Nachvollziehbare Protokollierung sicherheitsrelevanter Aktionen.

    T4 schreibt den Eintrag bei der Freigabe eines Änderungswunschs;
    T5 ergänzt Signale für Stammdaten-Änderungen und Login-Ereignisse.
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

    class Meta:
        ordering = ["-zeitpunkt"]

    def __str__(self):
        return f"{self.zeitpunkt:%Y-%m-%d %H:%M} · {self.aktion}"
