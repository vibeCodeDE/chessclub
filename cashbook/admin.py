from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from core.models import AuditLog

from .models import CashEntry
from .resources import CashEntryResource


@admin.register(CashEntry)
class CashEntryAdmin(ImportExportModelAdmin):
    resource_classes = [CashEntryResource]
    list_display = ("datum", "art", "kategorie", "betrag", "beschreibung", "belegnummer", "storno_von")
    list_filter = ("art", "kategorie", "datum")
    search_fields = ("beschreibung", "belegnummer")
    readonly_fields = ("storno_von", "erfasst_von", "erstellt_am")

    def has_delete_permission(self, request, obj=None):
        # Finanzdaten werden nie gelöscht – Korrektur erfolgt per Storno-Gegenbuchung (ADR-005, ADR-006).
        return False

    def get_data_for_export(self, request, queryset, **kwargs):
        export_data = super().get_data_for_export(request, queryset, **kwargs)
        if request.user.is_authenticated:
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Kassenbuch exportiert",
                text=f"{queryset.count()} Kassenbuchungen über den Django-Admin exportiert.",
            )
        return export_data

    def process_result(self, result, request):
        response = super().process_result(result, request)
        if request.user.is_authenticated and not result.has_errors():
            imported_count = len(result.rows)
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Kassenbuch importiert",
                text=f"{imported_count} Buchungen über den Django-Admin importiert.",
            )
        return response

    def get_import_resource_kwargs(self, request, **kwargs):
        resource_kwargs = super().get_import_resource_kwargs(request, **kwargs)
        resource_kwargs["user"] = request.user
        return resource_kwargs
