from django.contrib import admin

from core.models import AuditLog

from .models import FeeAmount, FeeCategory, FeePost


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


@admin.register(FeePost)
class FeePostAdmin(admin.ModelAdmin):
    """Posten sind Finanznachweis (PRD M2.2).

    Anlegen geht nur über den Beitragslauf, Löschen gar nicht — die Historie
    bleibt für den Kassenbericht (T11b) und § 147 AO erhalten. Eine Korrektur
    eines falschen Betrags ist möglich und wird mit Alt/Neu protokolliert.
    """

    list_display = ("member", "jahr", "kategorie", "betrag", "erstellt")
    list_filter = ("jahr", "kategorie")
    search_fields = ("member__nachname", "member__vorname")
    readonly_fields = ("member", "jahr", "erstellt")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Der alte Datensatz wird vor dem Speichern gelesen — danach ist er
        # nicht mehr abrufbar, und `.values()` liefert für FKs nur die ID.
        vorher = FeePost.objects.filter(pk=obj.pk).first() if change else None
        super().save_model(request, obj, form, change)
        if vorher is None:
            return
        aenderungen = []
        if vorher.kategorie_id != obj.kategorie_id:
            aenderungen.append(("kategorie", str(vorher.kategorie), str(obj.kategorie)))
        if vorher.betrag != obj.betrag:
            aenderungen.append(("betrag", str(vorher.betrag), str(obj.betrag)))
        for feld, alt, neu in aenderungen:
            AuditLog.objects.create(
                benutzer=request.user,
                aktion="Beitragsposten geändert",
                text=f"{obj.jahr} · {obj.member}",
                feld=feld,
                alt_wert=alt,
                neu_wert=neu,
                member=obj.member,
            )
