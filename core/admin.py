from django.contrib import admin

from .models import AuditLog, TwoFactorDevice


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Nur Einsehen – Audit-Einträge entstehen ausschließlich automatisch."""

    list_display = ("zeitpunkt", "benutzer", "aktion", "member", "feld")
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
        "neu_wert",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TwoFactorDevice)
class TwoFactorDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "bestaetigt", "erstellt_am", "letzte_nutzung")
    search_fields = ("user__username",)
    readonly_fields = ("secret", "erstellt_am", "letzte_nutzung")
