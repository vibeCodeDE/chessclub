from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


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
