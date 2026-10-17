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
    letzter_zeitschritt = models.BigIntegerField("Letzter Zeitschritt", null=True, blank=True)

    class Meta:
        verbose_name = "Zwei-Faktor-Gerät"
        verbose_name_plural = "Zwei-Faktor-Geräte"

    def __str__(self):
        return f"2FA für {self.user.get_username()}"


class ModuleSettings(models.Model):
    """Konfiguration aktiver Satellitenmodule des Vereins (T30, S7.4, ADR-019).

    Singleton-Muster: immer genau ein Datensatz (pk=1).
    Erlaubt es dem Superadmin / Vorstand, nicht genutzte Module
    (Spielbetrieb, Turniere, Kassenbuch, Kommunikation) im laufenden Betrieb
    in der UI und an den Routen zu deaktivieren.
    Kernmodule (core, members, dues) sind als Fundament nicht deaktivierbar.
    """

    homepage_aktiv = models.BooleanField(
        "Vereinshomepage (Öffentliche Webpräsenz)",
        default=True,
        help_text="Aktiviert die öffentliche Vereins-Startseite, Termine, Ansprechpartner und Vereinsdarstellung.",
    )
    spielbetrieb_aktiv = models.BooleanField(
        "Spielbetrieb & Mannschaften",
        default=True,
        help_text="Aktiviert Mannschaften, Ligaspiele, Aufstellungen und Ligatabellen.",
    )
    turniere_aktiv = models.BooleanField(
        "Turniere",
        default=True,
        help_text="Aktiviert Turnierverwaltung, öffentliche Anmeldung und Schweizer System.",
    )
    kassenbuch_aktiv = models.BooleanField(
        "Kassenbuch",
        default=True,
        help_text="Aktiviert das allgemeine Einnahmen-/Ausgaben-Kassenbuch.",
    )
    nachrichten_aktiv = models.BooleanField(
        "Kommunikation & News",
        default=True,
        help_text="Aktiviert Ankündigungen, News-Archiv und E-Mail-Rundschreiben.",
    )

    class Meta:
        verbose_name = "Modul-Einstellung"
        verbose_name_plural = "Modul-Einstellungen"

    def __str__(self):
        return "Modul-Einstellungen"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Löschen des Singleton-Datensatzes unterbinden

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DemoData(ModuleSettings):
    """Proxy-Modell für die Steuerung der Demo-Daten im Django Admin (ADR-022, S7.6, T34)."""

    class Meta:
        proxy = True
        verbose_name = "Demo-Daten"
        verbose_name_plural = "Demo-Daten (Ein/Aus)"


class ClubProfile(models.Model):
    """Stammdaten und Vereinsprofil des Schachvereins (ADR-020, T31).

    Singleton-Muster: immer genau ein Datensatz (pk=1).
    Erlaubt es dem Vorstand, Vereinsdaten, Spielabendzeiten und SEPA-Gläubiger-Daten
    direkt im Browser zu pflegen, ohne Umgebungsvariablen ändern zu müssen.
    Fallback auf Django-Settings greift, wenn DB-Felder leer sind.
    """

    name = models.CharField("Vereinsname", max_length=150, blank=True)
    kurzname = models.CharField("Kurzname / Kürzel", max_length=50, blank=True)
    zps_nummer = models.CharField("DSB-Vereinskennziffer", max_length=10, blank=True)
    kontakt_email = models.EmailField("Kontakt-E-Mail", blank=True)
    gruendungsjahr = models.CharField("Gründungsjahr", max_length=10, blank=True)
    ort = models.CharField("Ort", max_length=100, blank=True)
    spiellokal = models.CharField("Spiellokal / Anschrift", max_length=255, blank=True)
    spielabend_zeiten = models.CharField("Spielabend / Erwachsene", max_length=255, blank=True)
    jugend_zeiten = models.CharField("Jugendtraining", max_length=255, blank=True)
    beschreibung = models.TextField("Kurzbeschreibung", blank=True)

    # SEPA & Finanzen (für Lastschriften, Mahnbriefe und Mitgliedsanträge)
    sepa_glaeubiger_id = models.CharField("SEPA-Gläubiger-Identifikationsnummer", max_length=50, blank=True)
    sepa_glaeubiger_name = models.CharField("SEPA-Gläubiger-Name", max_length=150, blank=True)
    sepa_iban = models.CharField("Vereins-IBAN", max_length=50, blank=True)
    sepa_bic = models.CharField("Vereins-BIC", max_length=20, blank=True)

    class Meta:
        verbose_name = "Vereinsprofil"
        verbose_name_plural = "Vereinsprofil"

    def __str__(self):
        return self.name or getattr(settings, "CLUB_NAME", "Vereinsprofil")

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Löschen des Singleton-Datensatzes unterbinden

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class OnboardingProgress(models.Model):
    """Singleton zur Nachhaltung des Onboarding-Zustands eines Schachvereins."""

    aktueller_schritt = models.PositiveSmallIntegerField("Aktueller Schritt", default=1)
    schritte_abgeschlossen = models.JSONField("Abgeschlossene Schritte", default=list, blank=True)
    ist_abgeschlossen = models.BooleanField("Onboarding abgeschlossen", default=False)
    abgeschlossen_am = models.DateTimeField("Abgeschlossen am", null=True, blank=True)
    abgeschlossen_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Abgeschlossen von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="onboarding_abschluesse",
    )
    checklist_ausgeblendet = models.BooleanField("Dashboard-Checkliste ausgeblendet", default=False)

    class Meta:
        verbose_name = "Onboarding-Fortschritt"
        verbose_name_plural = "Onboarding-Fortschritt"

    def __str__(self):
        status = "Abgeschlossen" if self.ist_abgeschlossen else f"Schritt {self.aktueller_schritt}"
        return f"Onboarding: {status}"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def mark_step_completed(self, step_name: str, next_step: int | None = None):
        if not isinstance(self.schritte_abgeschlossen, list):
            self.schritte_abgeschlossen = []
        if step_name not in self.schritte_abgeschlossen:
            self.schritte_abgeschlossen.append(step_name)
        if next_step is not None and next_step > self.aktueller_schritt:
            self.aktueller_schritt = next_step
        self.save()

    @classmethod
    def is_onboarding_needed(cls) -> bool:
        progress = cls.get_solo()
        if progress.ist_abgeschlossen:
            return False
        club = ClubProfile.get_solo()
        return not bool(club.name)


class StaffInvitation(models.Model):
    """Temporäre Einladungen für Funktionäre (Vorstände & Mannschaftsführer)."""

    ROLLE_CHOICES = [
        ("admin", "Vorstand (Admin)"),
        ("kapitaen", "Mannschaftsführer (Kapitän)"),
    ]
    STATUS_CHOICES = [
        ("offen", "Offen"),
        ("angenommen", "Angenommen"),
        ("abgelaufen", "Abgelaufen"),
        ("widerrufen", "Widerrufen"),
    ]

    email = models.EmailField("E-Mail", db_index=True)
    vorname = models.CharField("Vorname", max_length=50)
    nachname = models.CharField("Nachname", max_length=50)
    rolle = models.CharField("Rolle", max_length=20, choices=ROLLE_CHOICES)
    token = models.CharField("Einladungs-Token", max_length=64, unique=True, db_index=True)
    status = models.CharField("Status", max_length=20, default="offen", choices=STATUS_CHOICES)
    gueltig_bis = models.DateTimeField("Gültig bis", db_index=True)
    erstellt_am = models.DateTimeField("Erstellt am", auto_now_add=True)
    angenommen_am = models.DateTimeField("Angenommen am", null=True, blank=True)
    eingeladen_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Eingeladen von",
        on_delete=models.CASCADE,
        related_name="ausgesprochene_einladungen",
    )
    benutzer = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Erstellter Benutzer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_invitation",
    )

    class Meta:
        verbose_name = "Funktionärseinladung"
        verbose_name_plural = "Funktionärseinladungen"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"Einladung an {self.email} ({self.get_rolle_display()}) - {self.status}"

    @property
    def is_valid(self) -> bool:
        return self.status == "offen" and timezone.now() <= self.gueltig_bis


