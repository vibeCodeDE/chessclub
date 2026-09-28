from django.contrib import admin

from .models import FeeAmount, FeeCategory


class FeeAmountInline(admin.TabularInline):
    """Beträge je Jahr direkt an der Kategorie pflegen (T7)."""

    model = FeeAmount
    extra = 1
    ordering = ("jahr",)
    fields = ("jahr", "betrag")


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ("bezeichnung", "code", "aktiv", "anzahl_jahre")
    list_filter = ("aktiv",)
    search_fields = ("bezeichnung", "code")
    inlines = [FeeAmountInline]

    @admin.display(description="Jahre")
    def anzahl_jahre(self, obj):
        return obj.betraege.count()


@admin.register(FeeAmount)
class FeeAmountAdmin(admin.ModelAdmin):
    list_display = ("kategorie", "jahr", "betrag")
    list_filter = ("kategorie", "jahr")
    ordering = ("kategorie__bezeichnung", "jahr")
