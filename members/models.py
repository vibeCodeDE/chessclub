import secrets

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone


def generate_ical_token():
    return secrets.token_urlsafe(24)


class Member(models.Model):
    """Stammdaten eines Mitglieds (PRD M1.1/M1.3).

    Mitglieder werden nie hart gelöscht, sondern auf „ausgetreten“ gesetzt;
    jeder Statuswechsel wird in :class:`MemberStatusChange` historisiert.
    """

    class Status(models.TextChoices):
        AKTIV = "aktiv", "Aktiv"
        PASSIV = "passiv", "Passiv"
        AUSGETRETEN = "ausgetreten", "Ausgetreten"

    class Spielberechtigung(models.TextChoices):
        ERST = "erst", "Erstmitgliedschaft"
        ZWEIT = "zweit", "Zweitmitgliedschaft (Gast)"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Benutzerkonto",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="member",
    )
    vorname = models.CharField("Vorname", max_length=100)
    nachname = models.CharField("Nachname", max_length=100)
    geburtsdatum = models.DateField("Geburtsdatum", null=True, blank=True)
    strasse = models.CharField("Straße/Nr.", max_length=200, blank=True)
    plz = models.CharField("PLZ", max_length=10, blank=True)
    ort = models.CharField("Ort", max_length=100, blank=True)
    email = models.EmailField("E-Mail", blank=True)
    telefon = models.CharField("Telefon", max_length=50, blank=True)
    eintrittsdatum = models.DateField("Eintrittsdatum")
    austrittsdatum = models.DateField("Austrittsdatum", null=True, blank=True)
    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.AKTIV,
    )
    beitragskategorie = models.ForeignKey(
        "dues.FeeCategory",
        verbose_name="Beitragskategorie",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mitglieder",
    )
    email_opt_in = models.BooleanField(
        "E-Mail-Rundbrief erlaubt",
        default=True,
        help_text="Opt-in für Gruppen-E-Mails (PRD M5.2).",
    )
    # ADR-016: Bundeseinheitliche Verbandskennungen und Wertungszahlen
    zps_nummer = models.CharField(
        "ZPS-Nummer",
        max_length=20,
        blank=True,
        help_text="ZPS-Passnummer (z. B. C0101-042).",
    )
    pkz = models.CharField(
        "PKZ",
        max_length=20,
        blank=True,
        help_text="Personenkennziffer im DSB-System.",
    )
    dwz = models.PositiveIntegerField("DWZ", null=True, blank=True)
    dwz_index = models.PositiveIntegerField("DWZ-Index", null=True, blank=True)
    fide_id = models.PositiveIntegerField("FIDE-ID", null=True, blank=True)
    spielberechtigung = models.CharField(
        "Spielberechtigung",
        max_length=20,
        choices=Spielberechtigung.choices,
        default=Spielberechtigung.ERST,
        blank=True,
    )
    anonymisiert_am = models.DateTimeField(
        "Anonymisiert am",
        null=True,
        blank=True,
        help_text="Gesetzt, wenn Kontaktdaten nach der Aufbewahrungsfrist entfernt wurden (PRD N1.3).",
    )
    ical_token = models.CharField(
        "iCal-Token",
        max_length=64,
        unique=True,
        default=generate_ical_token,
    )

    class Meta:
        ordering = ["nachname", "vorname"]

    def __str__(self):
        return f"{self.nachname}, {self.vorname}"

    def renew_ical_token(self):
        self.ical_token = generate_ical_token()
        self.save(update_fields=["ical_token"])
        return self.ical_token

    @property
    def dwz_formatiert(self):
        """Formatierte DWZ mit Index, z. B. '1850-45'."""
        if self.dwz is None:
            return ""
        if self.dwz_index is not None:
            return f"{self.dwz}-{self.dwz_index}"
        return str(self.dwz)

    def clean(self):
        super().clean()
        errors = {}
        if (
            self.eintrittsdatum
            and self.austrittsdatum
            and self.austrittsdatum < self.eintrittsdatum
        ):
            errors["austrittsdatum"] = "Das Austrittsdatum liegt vor dem Eintrittsdatum."
        if self.status == self.Status.AUSGETRETEN and not self.austrittsdatum:
            errors["austrittsdatum"] = (
                "Bei Status „ausgetreten“ ist ein Austrittsdatum erforderlich."
            )
        if self.status != self.Status.AUSGETRETEN and self.austrittsdatum:
            errors["austrittsdatum"] = (
                "Ein Austrittsdatum ist nur beim Status „ausgetreten“ erlaubt."
            )
        if self.status == self.Status.AUSGETRETEN and self.beitragskategorie_id:
            errors["beitragskategorie"] = (
                "Ein ausgetretenes Mitglied kann keiner Beitragskategorie zugeordnet werden."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        previous_status = None
        if self.pk:
            previous_status = (
                Member.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )
        super().save(*args, **kwargs)
        if previous_status is not None and previous_status != self.status:
            MemberStatusChange.objects.create(
                member=self,
                von=previous_status,
                nach=self.status,
                # Admin setzt _changed_by in MemberAdmin.save_model;
                # Änderungen ohne diesen Kontext bleiben ohne Benutzer.
                geaendert_von=getattr(self, "_changed_by", None),
            )

    def delete(self, *args, **kwargs):
        # PRD M1.3: kein Löschen, sondern Deaktivieren.
        self.status = self.Status.AUSGETRETEN
        if not self.austrittsdatum:
            self.austrittsdatum = timezone.localdate()
        self.save()


class MemberStatusChange(models.Model):
    member = models.ForeignKey(
        Member,
        verbose_name="Mitglied",
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    von = models.CharField("Von", max_length=20, choices=Member.Status.choices)
    nach = models.CharField("Nach", max_length=20, choices=Member.Status.choices)
    zeitpunkt = models.DateTimeField("Zeitpunkt", auto_now_add=True)
    geaendert_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Geändert von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="member_status_changes",
    )

    class Meta:
        ordering = ["-zeitpunkt"]

    def __str__(self):
        return f"{self.member}: {self.von} → {self.nach}"


# PRD M1.4: Mitglieder ändern nichts direkt, sondern reichen Wünsche für
# genau diese Felder ein; alles andere (Status, Daten, Beträge) bleibt Admin-Sache.
EDITABLE_FIELDS = {
    "strasse": "Straße/Nr.",
    "plz": "PLZ",
    "ort": "Ort",
    "email": "E-Mail",
    "telefon": "Telefon",
}


def clean_member_value(feld, value):
    """Validiert ``value`` als neuen Wert für das Mitgliedsfeld ``feld``.

    Gibt den bereinigten Wert zurück, sonst :class:`ValidationError`.
    """
    if feld not in EDITABLE_FIELDS:
        raise ValidationError({"feld": "Für dieses Feld sind keine Änderungswünsche möglich."})
    try:
        model_field = Member._meta.get_field(feld)
    except FieldDoesNotExist:
        raise ValidationError({"feld": "Unbekanntes Feld."}) from None
    try:
        return model_field.clean(value, None)
    except ValidationError as exc:
        raise ValidationError({"wunschwert": exc.messages}) from exc


class ChangeRequest(models.Model):
    """Änderungswunsch eines Mitglieds (PRD M1.4).

    Ohne Freigabe durch den Vorstand bleibt das Stammdatum unangetastet;
    erst die Freigabe überträgt den Wert und schreibt einen Audit-Eintrag.
    """

    class Status(models.TextChoices):
        EINGEREICHT = "eingereicht", "Eingereicht"
        FREIGEGEBEN = "freigegeben", "Freigegeben"
        ABGELEHNT = "abgelehnt", "Abgelehnt"

    member = models.ForeignKey(
        Member,
        verbose_name="Mitglied",
        on_delete=models.CASCADE,
        related_name="change_requests",
    )
    feld = models.CharField("Feld", max_length=20, choices=list(EDITABLE_FIELDS.items()))
    wunschwert = models.CharField("Wunschwert", max_length=200)
    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.EINGEREICHT,
    )
    eingereicht_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Eingereicht von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="change_requests",
    )
    eingereicht_am = models.DateTimeField("Eingereicht am", auto_now_add=True)
    entschieden_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Entschieden von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="change_decisions",
    )
    entschieden_am = models.DateTimeField("Entschieden am", null=True, blank=True)
    kommentar = models.CharField("Kommentar", max_length=500, blank=True)

    class Meta:
        ordering = ["-eingereicht_am"]

    def __str__(self):
        return f"{self.member}: {self.get_feld_display()} → {self.wunschwert}"

    @property
    def aktueller_wert(self):
        """Der derzeit in den Stammdaten stehende Wert (Anzeige bei der Prüfung)."""
        return str(getattr(self.member, self.feld, "") or "")

    def clean(self):
        super().clean()
        if self.feld and self.wunschwert:
            clean_member_value(self.feld, self.wunschwert)
