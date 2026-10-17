from django.contrib import admin

from .models import (
    AuditLog,
    ClubProfile,
    DemoData,
    ModuleSettings,
    OnboardingProgress,
    StaffInvitation,
    TwoFactorDevice,
)


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

    def get_results(self, request, queryset, *args, **kwargs):
        """Lookup-Tabelle Beitragskategorien einmal je Seitenaufruf laden.

        Sonst fragt die Anzeige des alten/neuen Werts je Zeile ab (N+1).
        """
        seite, _ = super().get_results(request, queryset, *args, **kwargs)
        if seite is not None and any(obj.feld == "beitragskategorie" for obj in seite):
            from dues.models import FeeCategory

            namen = {k.pk: str(k) for k in FeeCategory.objects.all()}
            for obj in seite:
                obj.kategorie_namen = namen
        return seite, _

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


@admin.register(ModuleSettings)
class ModuleSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "homepage_aktiv",
        "spielbetrieb_aktiv",
        "turniere_aktiv",
        "kassenbuch_aktiv",
        "nachrichten_aktiv",
    )

    def has_add_permission(self, request):
        return not ModuleSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and form.changed_data:
            geaendert = ", ".join(
                f"{f}: {form.cleaned_data.get(f)}" for f in form.changed_data
            )
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Modul-Einstellungen geändert",
                text=f"Geänderte Module: {geaendert}",
            )


@admin.register(ClubProfile)
class ClubProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "kurzname", "kontakt_email", "ort", "sepa_glaeubiger_id")

    def has_add_permission(self, request):
        return not ClubProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if form.changed_data:
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Vereinsprofil im Admin geändert",
                text=f"Geänderte Felder: {', '.join(form.changed_data)}",
            )


@admin.register(DemoData)
class DemoDataAdmin(admin.ModelAdmin):
    change_list_template = "admin/core/demodata/change_list.html"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name="admin").exists()

    def changelist_view(self, request, extra_context=None):
        from django.contrib import messages
        from django.core.exceptions import PermissionDenied
        from django.shortcuts import redirect
        from django.template.response import TemplateResponse

        from .services import (
            get_demo_data_status,
            install_demo_data,
            remove_demo_data,
        )

        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method == "POST":
            action = request.POST.get("action")
            if action == "load":
                success, msg = install_demo_data(user=request.user)
                if success:
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
            elif action == "remove":
                confirm = request.POST.get("confirm") == "1"
                success, msg = remove_demo_data(user=request.user, confirm=confirm)
                if success:
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)
            return redirect("admin:core_demodata_changelist")

        status_info = get_demo_data_status()
        letzte_audits = AuditLog.objects.filter(aktion__icontains="Demo")[:10]

        context = {
            **self.admin_site.each_context(request),
            "title": "Demo-Daten-Verwaltung",
            "status_info": status_info,
            "letzte_audits": letzte_audits,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, self.change_list_template, context)


@admin.register(OnboardingProgress)
class OnboardingProgressAdmin(admin.ModelAdmin):
    """Zustand des Vereins-Onboardings (Singleton, revisionssicher)."""

    list_display = (
        "__str__",
        "aktueller_schritt",
        "ist_abgeschlossen",
        "abgeschlossen_am",
        "abgeschlossen_von",
        "checklist_ausgeblendet",
    )
    readonly_fields = (
        "aktueller_schritt",
        "schritte_abgeschlossen",
        "ist_abgeschlossen",
        "abgeschlossen_am",
        "abgeschlossen_von",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StaffInvitation)
class StaffInvitationAdmin(admin.ModelAdmin):
    """Verwaltung von Funktionärseinladungen mit Revisionssicherheit."""

    list_display = (
        "email",
        "vorname",
        "nachname",
        "rolle",
        "status",
        "gueltig_bis",
        "erstellt_am",
        "angenommen_am",
    )
    list_filter = ("status", "rolle")
    search_fields = ("email", "vorname", "nachname")
    readonly_fields = ("token", "erstellt_am", "angenommen_am", "benutzer")

    def has_delete_permission(self, request, obj=None):
        return False



