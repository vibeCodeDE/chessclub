"""Import/Export-Ressourcen für Kassenbuchungen (PRD S6.1, S6.2, ADR-021)."""

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from .models import CashEntry


class CashEntryResource(resources.ModelResource):
    """Ressource für den strukturierten Import/Export von Kassenbuchungen."""

    storno_von = fields.Field(
        column_name="storno_von",
        attribute="storno_von",
        widget=ForeignKeyWidget(CashEntry, field="id"),
    )

    class Meta:
        model = CashEntry
        fields = (
            "id",
            "datum",
            "art",
            "kategorie",
            "betrag",
            "beschreibung",
            "belegnummer",
            "storno_von",
        )
        export_order = (
            "id",
            "datum",
            "art",
            "kategorie",
            "betrag",
            "beschreibung",
            "belegnummer",
            "storno_von",
        )
        clean_model_instances = True
        skip_unchanged = True
        report_skipped = True

    def before_save_instance(self, instance, row, **kwargs):
        user = kwargs.get("user")
        if user and not instance.erfasst_von_id:
            instance.erfasst_von = user
        return super().before_save_instance(instance, row, **kwargs)
