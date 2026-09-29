from django.contrib import admin

from .models import CashEntry


@admin.register(CashEntry)
class CashEntryAdmin(admin.ModelAdmin):
    list_display = ("datum", "art", "kategorie", "betrag", "beschreibung", "belegnummer")
    list_filter = ("art", "kategorie", "datum")
    search_fields = ("beschreibung", "belegnummer")
