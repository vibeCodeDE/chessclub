from django.contrib import admin

from core.models import AuditLog

from .models import ChangeRequest, Member, MemberStatusChange


class MemberStatusChangeInline(admin.TabularInline):
    model = MemberStatusChange
    extra = 0
    can_delete = False
    fields = ("zeitpunkt", "von", "nach", "geaendert_von")
    readonly_fields = ("zeitpunkt", "von", "nach", "geaendert_von")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "nachname",
        "vorname",
        "status",
        "beitragskategorie",
        "ort",
        "eintrittsdatum",
        "email",
    )
    list_filter = ("status", "beitragskategorie")
    search_fields = ("vorname", "nachname", "email", "ort")
    ordering = ("nachname", "vorname")
    inlines = [MemberStatusChangeInline]

    def has_delete_permission(self, request, obj=None):
        # PRD M1.3: kein Löschen von Mitgliedern.
        return False

    def save_model(self, request, obj, form, change):
        obj._changed_by = request.user
        super().save_model(request, obj, form, change)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.method == "GET" and request.user.is_authenticated:
            member = self.get_object(request, object_id)
            if member:
                AuditLog.objects.create(
                    benutzer=request.user,
                    aktion="Mitgliedsakte eingesehen",
                    text=f"Stammdaten und Akte von {member} im Admin aufgerufen.",
                    member=member,
                )
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    """Nur einsehen – Freigabe/Ablehnung läuft ausschließlich über die UI (T4)."""

    list_display = ("member", "feld", "wunschwert", "status", "eingereicht_am", "entschieden_von")
    list_filter = ("status", "feld")
    search_fields = ("member__nachname", "member__vorname", "wunschwert")
    readonly_fields = (
        "member",
        "feld",
        "wunschwert",
        "status",
        "eingereicht_von",
        "eingereicht_am",
        "entschieden_von",
        "entschieden_am",
        "kommentar",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
