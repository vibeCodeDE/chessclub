from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Nur Einsehen – Audit-Einträge entstehen ausschließlich automatisch."""

    list_display = ("zeitpunkt", "benutzer", "aktion", "member", "feld", "neuer_wert")
    list_filter = ("aktion", "zeitpunkt")
    search_fields = (
        "benutzer__username",
        "text",
        "member__nachname",
        "member__vorname",
    )
    readonly_fields = (
        "zeitpunkt",
        "benutzer",
        "aktion",
        "text",
        "member",
        "feld",
        "alt_wert",
        "neuer_wert",
    )

    @admin.display(description="Neuer Wert", ordering="neu_wert")
    def neuer_wert(self, obj):
        """FK-IDs als Objekt beschriften – eine Datenbank-ID ist kein Lesewert."""
        return obj.anzeige_wert()

    @admin.display(description="Alter Wert", ordering="alt_wert")
    def alter_wert(self, obj):
        return obj.anzeige_wert(obj.alt_wert)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
