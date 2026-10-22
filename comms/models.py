"""News/Ankündigungen im Portal (PRD M5.1)."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class NewsPost(models.Model):
    """Ankündigung mit Entwurfs-Workflow und Archiv."""

    titel = models.CharField("Titel", max_length=200)
    text = models.TextField("Text")
    kategorie = models.CharField("Kategorie", max_length=50, blank=True, default="Verein")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Autor:in",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="news_posts",
    )
    veroeffentlicht = models.BooleanField("Veröffentlicht", default=False)
    veroeffentlicht_am = models.DateTimeField("Veröffentlicht am", null=True, blank=True)
    erstellt_am = models.DateTimeField("Erstellt am", auto_now_add=True)
    geaendert_am = models.DateTimeField("Geändert am", auto_now=True)

    class Meta:
        verbose_name = "Ankündigung"
        verbose_name_plural = "Ankündigungen"
        ordering = ["-veroeffentlicht_am", "-erstellt_am"]

    def __str__(self):
        return self.titel

    @property
    def auszug(self):
        text = " ".join(self.text.split())
        return text if len(text) <= 180 else text[:177].rstrip() + "…"

    @property
    def ist_entwurf(self):
        return not self.veroeffentlicht

    def veroeffentlichen(self, commit=True):
        self.veroeffentlicht = True
        if not self.veroeffentlicht_am:
            self.veroeffentlicht_am = timezone.now()
        if commit:
            self.save(update_fields=["veroeffentlicht", "veroeffentlicht_am", "geaendert_am"])
        return self

    def zurueckziehen(self, commit=True):
        self.veroeffentlicht = False
        if commit:
            self.save(update_fields=["veroeffentlicht", "geaendert_am"])
        return self


class MailLog(models.Model):
    """Protokoll eines Gruppen-E-Mail-Versands (PRD M5.2/N1.5)."""

    class Status(models.TextChoices):
        QUEUED = "queued", "In Warteschlange"
        GESENDET = "gesendet", "Gesendet"
        TEILWEISE = "teilweise", "Teilweise gesendet"
        FEHLGESCHLAGEN = "fehlgeschlagen", "Fehlgeschlagen"
        TEST = "test", "Testversand"

    class Zielgruppe(models.TextChoices):
        AKTIV = "aktiv", "Aktive Mitglieder"
        ALLE = "alle", "Alle Mitglieder (aktiv und passiv)"
        PASSIV = "passiv", "Passive Mitglieder"
        VORSTAND = "vorstand", "Vorstand (Rolle admin)"
        KAPITAENE = "kapitaene", "Mannschaftsführer (Rolle kapitaen)"

    betreff = models.CharField("Betreff", max_length=200)
    text = models.TextField("Text")
    zielgruppe = models.CharField("Zielgruppe", max_length=20, choices=Zielgruppe.choices)
    anzahl_empfaenger = models.PositiveIntegerField("Empfänger:innen", default=0)
    anzahl_uebersprungen = models.PositiveIntegerField("Übersprungen (kein Opt-in)", default=0)
    anzahl_fehler = models.PositiveIntegerField("Fehlgeschlagen", default=0)
    status = models.CharField("Status", max_length=20, choices=Status.choices)
    test_empfaenger = models.CharField("Testadresse(n)", max_length=300, blank=True)
    erstellt_am = models.DateTimeField("Gesendet am", auto_now_add=True)
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Gesendet von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mail_logs",
    )

    class Meta:
        verbose_name = "E-Mail-Versand"
        verbose_name_plural = "E-Mail-Protokoll"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"{self.betreff} ({self.get_zielgruppe_display()})"

    @property
    def status_badge(self):
        return {
            self.Status.QUEUED: "badge-warnung",
            self.Status.GESENDET: "badge-bezahlt",
            self.Status.TEILWEISE: "badge-warnung",
            self.Status.FEHLGESCHLAGEN: "badge-offen",
            self.Status.TEST: "badge-entwurf",
        }.get(self.status, "badge-entwurf")


class QueuedMail(models.Model):
    """Ausstehende E-Mail in der schlanken Versand-Warteschlange (T38).

    Ermöglicht blockweisen, asynchronen Versand großer Empfängermengen
    ohne Abhängigkeit von Celery/Redis.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Ausstehend"
        SENT = "sent", "Gesendet"
        FAILED = "failed", "Fehlgeschlagen"

    mail_log = models.ForeignKey(
        MailLog,
        verbose_name="E-Mail-Protokoll",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="queued_mails",
    )
    empfaenger_email = models.EmailField("Empfänger-E-Mail")
    betreff = models.CharField("Betreff", max_length=200)
    text = models.TextField("Text")
    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    versuche = models.PositiveIntegerField("Versuche", default=0)
    fehler_meldung = models.TextField("Fehlermeldung", blank=True)
    erstellt_am = models.DateTimeField("Erstellt am", auto_now_add=True)
    gesendet_am = models.DateTimeField("Gesendet am", null=True, blank=True)

    class Meta:
        verbose_name = "Warteschlangen-E-Mail"
        verbose_name_plural = "Warteschlangen-E-Mails"
        ordering = ["erstellt_am"]

    def __str__(self):
        return f"{self.empfaenger_email} - {self.betreff} ({self.status})"

