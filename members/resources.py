"""Import/Export-Ressourcen für Mitgliederstammdaten (PRD M1.5, S1.7, ADR-021)."""

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from dues.models import FeeCategory

from .models import Member


class MemberResource(resources.ModelResource):
    """Ressource für den strukturierten Import/Export von Mitgliedern im Django-Admin."""

    beitragskategorie = fields.Field(
        column_name="beitragskategorie",
        attribute="beitragskategorie",
        widget=ForeignKeyWidget(FeeCategory, field="name"),
    )

    class Meta:
        model = Member
        fields = (
            "id",
            "nachname",
            "vorname",
            "geburtsdatum",
            "strasse",
            "plz",
            "ort",
            "email",
            "telefon",
            "eintrittsdatum",
            "austrittsdatum",
            "status",
            "beitragskategorie",
            "email_opt_in",
            "zps_nummer",
            "pkz",
            "dwz",
            "dwz_index",
            "fide_id",
            "spielberechtigung",
        )
        export_order = (
            "id",
            "nachname",
            "vorname",
            "status",
            "beitragskategorie",
            "geburtsdatum",
            "email",
            "telefon",
            "strasse",
            "plz",
            "ort",
            "eintrittsdatum",
            "austrittsdatum",
            "email_opt_in",
            "zps_nummer",
            "pkz",
            "dwz",
            "dwz_index",
            "fide_id",
            "spielberechtigung",
        )
        clean_model_instances = True
        skip_unchanged = True
        report_skipped = True

    def before_save_instance(self, instance, row, **kwargs):
        user = kwargs.get("user")
        if user:
            instance._changed_by = user
        return super().before_save_instance(instance, row, **kwargs)
