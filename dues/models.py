from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class FeeCategory(models.Model):
    """Beitragskategorie des Vereins (PRD M2.1).

    Die Kategorie ist die jahresunabhängige Identität (Erwachsene, Jugend,
    Familie, ermäßigt). Der konkrete Betrag steht je Jahr in :class:`FeeAmount`
    — dadurch ändert ein neuer Satz für 2027 den Wert für 2026 nicht.
    """

    code = models.SlugField("Code", max_length=50, unique=True)
    bezeichnung = models.CharField("Bezeichnung", max_length=100)
    aktiv = models.BooleanField("Aktiv", default=True)

    class Meta:
        ordering = ["bezeichnung"]
        verbose_name_plural = "Beitragskategorien"

    def __str__(self):
        return self.bezeichnung


class FeeAmount(models.Model):
    """Beitragssatz einer Kategorie für genau ein Jahr."""

    kategorie = models.ForeignKey(
        FeeCategory,
        verbose_name="Kategorie",
        on_delete=models.CASCADE,
        related_name="betraege",
    )
    jahr = models.PositiveIntegerField("Jahr")
    betrag = models.DecimalField(
        "Betrag",
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        ordering = ["kategorie__bezeichnung", "jahr"]
        constraints = [
            models.UniqueConstraint(
                fields=["kategorie", "jahr"],
                name="unique_fee_amount_per_kategorie_jahr",
            )
        ]
        verbose_name_plural = "Beitragssätze"

    def __str__(self):
        if self.betrag is None:
            return f"{self.kategorie} {self.jahr}: —"
        # Deutsches Zahlenformat, die App ist durchgängig deutschsprachig.
        betrag = f"{self.betrag:.2f}".replace(".", ",")
        return f"{self.kategorie} {self.jahr}: {betrag} €"

    def clean(self):
        super().clean()
        # MinValueValidator greift nur über full_clean()/Formulare; der
        # explizite Check macht die Regel auch im Service-/Testpfad sichtbar.
        if self.betrag is not None and self.betrag < 0:
            raise ValidationError({"betrag": "Der Betrag darf nicht negativ sein."})


class FeePost(models.Model):
    """Beitragsposten eines Mitglieds für ein Beitragsjahr (PRD M2.2).

    Der Posten entsteht ausschließlich über den Beitragslauf
    (:func:`dues.services.fuehre_lauf`) und ist ein Finanznachweis: Kategorie
    und Betrag werden als Momentaufnahme kopiert, damit eine spätere Änderung
    am :class:`FeeAmount` die gebuchte Historie nicht überschreibt.
    """

    member = models.ForeignKey(
        "members.Member",
        verbose_name="Mitglied",
        # Kein Hard-Delete: die Finanzhistorie bleibt nach § 147 AO erhalten.
        on_delete=models.PROTECT,
        related_name="beitragsposten",
    )
    jahr = models.PositiveIntegerField("Jahr")
    kategorie = models.ForeignKey(
        FeeCategory,
        verbose_name="Kategorie",
        on_delete=models.PROTECT,
        related_name="posten",
    )
    betrag = models.DecimalField(
        "Betrag", max_digits=6, decimal_places=2, validators=[MinValueValidator(0)]
    )
    erstellt = models.DateTimeField("Erstellt", auto_now_add=True)

    class Meta:
        ordering = ["-jahr", "member__nachname", "member__vorname"]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "jahr"],
                name="unique_fee_post_per_member_jahr",
            )
        ]
        verbose_name = "Beitragsposten"
        verbose_name_plural = "Beitragsposten"

    def __str__(self):
        betrag = f"{self.betrag:.2f}".replace(".", ",")
        return f"{self.jahr} · {self.member} · {betrag} €"


class SepaMandate(models.Model):
    """SEPA-Mandat eines Mitglieds (PRD M2.3).

    Verwaltet wird nur, was der Einzug braucht: Referenz, Datum, Status. Die
    IBAN liegt beim Verein in der Lastschriftdatei der Bank — die Software
    nimmt **keinen** Einzug vor, sondern nur den Zahlungsstatus (PRD M2.3,
    Entscheidung Nr. 2). Deshalb wird hier bewusst keine IBAN gespeichert.

    Ein Mandatswechsel (neue Bankverbindung) erzeugt einen neuen Datensatz;
    der alte behält ``widerrufen`` bzw. ``beendet``. Maßgeblich ist, ob ein
    Mandat **aktiv** ist (:func:`dues.services.hat_sepa_mandat`).
    """

    class Status(models.TextChoices):
        AKTIV = "aktiv", "Aktiv"
        WIDERRUFEN = "widerrufen", "Widerrufen"
        BEENDET = "beendet", "Beendet"

    member = models.ForeignKey(
        "members.Member",
        verbose_name="Mitglied",
        # Mandate sind Finanznachweis — kein Hard-Delete an der Historie.
        on_delete=models.PROTECT,
        related_name="sepa_mandate",
    )
    referenz = models.CharField("Referenz", max_length=50, unique=True)
    datum = models.DateField("Mandatsdatum", default=timezone.localdate)
    status = models.CharField(
        "Status", max_length=20, choices=Status.choices, default=Status.AKTIV
    )
    notiz = models.TextField("Notiz", blank=True)

    class Meta:
        ordering = ["-datum", "member__nachname"]
        verbose_name = "SEPA-Mandat"
        verbose_name_plural = "SEPA-Mandate"

    def __str__(self):
        return f"{self.member} · {self.referenz}"


class Payment(models.Model):
    """Zahlung auf einen Beitragsposten (PRD M2.4).

    Von Hand gebucht: Überweisung, SEPA-Einzug oder Barzahlung. Ein
    **negativer** Betrag ist eine Gegenbuchung (Storno) — Zahlungen werden nie
    gelöscht, damit die Finanzhistorie nach § 147 AO nachvollziehbar bleibt.
    """

    class Art(models.TextChoices):
        SEPA = "sepa", "SEPA-Einzug"
        UEBERWEISUNG = "ueberweisung", "Überweisung"
        BAR = "bar", "Barzahlung"

    post = models.ForeignKey(
        FeePost,
        verbose_name="Beitragsposten",
        on_delete=models.PROTECT,
        related_name="zahlungen",
    )
    # Bewusst ohne MinValueValidator: ein negativer Betrag ist ein Storno.
    betrag = models.DecimalField("Betrag", max_digits=6, decimal_places=2)
    art = models.CharField("Zahlungsart", max_length=20, choices=Art.choices)
    datum = models.DateField("Zahlungsdatum", default=timezone.localdate)
    referenz = models.CharField("Referenz", max_length=100, blank=True)
    storno_von = models.ForeignKey(
        "self",
        verbose_name="Storno zu",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stornos",
    )
    notiz = models.TextField("Notiz", blank=True)
    erfasst = models.DateTimeField("Erfasst", auto_now_add=True)
    erfasst_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Erfasst von",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="erfasste_zahlungen",
    )

    class Meta:
        ordering = ["-datum", "-pk"]
        verbose_name = "Zahlung"
        verbose_name_plural = "Zahlungen"

    def __str__(self):
        betrag = f"{self.betrag:.2f}".replace(".", ",")
        return f"{self.get_art_display()} {self.datum}: {betrag} €"

    def clean(self):
        super().clean()
        if self.betrag == 0:
            raise ValidationError({"betrag": "Der Betrag darf nicht 0,00 € sein."})
        if self.art == self.Art.SEPA and self.post_id:
            if not SepaMandate.objects.filter(
                member_id=self.post.member_id, status=SepaMandate.Status.AKTIV
            ).exists():
                raise ValidationError(
                    {
                        "art": "Für einen SEPA-Einzug wird ein aktives SEPA-Mandat "
                        "des Mitglieds benötigt — bitte es unter „Zahlungen“ "
                        "zuerst anlegen."
                    }
                )
