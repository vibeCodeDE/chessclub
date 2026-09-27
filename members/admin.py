from django.contrib import admin

from .models import Member, MemberStatusChange


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
    list_display = ("nachname", "vorname", "status", "ort", "eintrittsdatum", "email")
    list_filter = ("status",)
    search_fields = ("vorname", "nachname", "email", "ort")
    ordering = ("nachname", "vorname")
    inlines = [MemberStatusChangeInline]

    def has_delete_permission(self, request, obj=None):
        # PRD M1.3: kein Löschen von Mitgliedern.
        return False

    def save_model(self, request, obj, form, change):
        obj._changed_by = request.user
        super().save_model(request, obj, form, change)
