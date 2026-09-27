from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Member(models.Model):
    """Stammdaten eines Mitglieds (PRD M1.1/M1.3).

    Mitglieder werden nie hart gelöscht, sondern auf „ausgetreten“ gesetzt;
    jeder Statuswechsel wird in :class:`MemberStatusChange` historisiert.
    """

    class Status(models.TextChoices):
        AKTIV = "aktiv", "Aktiv"
        PASSIV = "passiv", "Passiv"
        AUSGETRETEN = "ausgetreten", "Ausgetreten"

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

    class Meta:
        ordering = ["nachname", "vorname"]

    def __str__(self):
        return f"{self.nachname}, {self.vorname}"

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
