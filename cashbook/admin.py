from django.contrib import admin

from .models import CashEntry


@admin.register(CashEntry)
class CashEntryAdmin(admin.ModelAdmin):
    list_display = ("datum", "art", "kategorie", "betrag", "beschreibung", "belegnummer", "storno_von")
    list_filter = ("art", "kategorie", "datum")
    search_fields = ("beschreibung", "belegnummer")
    readonly_fields = ("storno_von", "erfasst_von", "erstellt_am")

    def has_delete_permission(self, request, obj=None):
        # Finanzdaten werden nie gelöscht – Korrektur erfolgt per Storno-Gegenbuchung.
        return False
