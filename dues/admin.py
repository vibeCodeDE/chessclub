from django.contrib import admin

from core.models import AuditLog

from .models import (
    DunningLetter,
    FeeAmount,
    FeeCategory,
    MembershipFee,
    Payment,
    SepaMandate,
)


class FeeAmountInline(admin.TabularInline):
    model = FeeAmount
    extra = 1


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "aktueller_betrag_display", "aktiv", "mitglieder_anzahl")
    list_filter = ("aktiv",)
    search_fields = ("name",)
    inlines = [FeeAmountInline]

    @admin.display(description="Jahresbeitrag (aktuell)")
    def aktueller_betrag_display(self, obj):
        betrag = obj.aktueller_betrag
        return f"{betrag:.2f} €" if betrag is not None else "–"


@admin.register(FeeAmount)
class FeeAmountAdmin(admin.ModelAdmin):
    list_display = ("kategorie", "jahr", "betrag")
    list_filter = ("jahr", "kategorie")
    search_fields = ("kategorie__name",)


@admin.register(SepaMandate)
class SepaMandateAdmin(admin.ModelAdmin):
    list_display = ("member", "referenz", "iban_kurz", "status", "erteilt_am")
    list_filter = ("status",)
    search_fields = ("member__nachname", "member__vorname", "referenz")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.method == "GET" and request.user.is_authenticated:
            mandat = self.get_object(request, object_id)
            if mandat and mandat.member:
                AuditLog.objects.create(
                    benutzer=request.user,
                    aktion="SEPA-Mandat eingesehen",
                    text=f"SEPA-Mandat {mandat.referenz} von {mandat.member} im Admin aufgerufen.",
                    member=mandat.member,
                )
        return super().change_view(request, object_id, form_url, extra_context)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    fields = ("betrag", "datum", "art", "notiz", "storno_von")
    readonly_fields = ("storno_von",)


@admin.register(MembershipFee)
class MembershipFeeAdmin(admin.ModelAdmin):
    list_display = ("member", "jahr", "kategorie_name", "betrag", "status", "mahnstufe")
    list_filter = ("jahr", "status")
    search_fields = ("member__nachname", "member__vorname")
    inlines = [PaymentInline]

    def has_delete_permission(self, request, obj=None):
        # Finanzdaten werden nie gelöscht.
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("datum", "fee", "betrag", "art", "notiz", "storno_von", "erfasst_von")
    list_filter = ("art", "datum")
    search_fields = ("fee__member__nachname", "fee__member__vorname", "notiz")
    readonly_fields = ("storno_von", "kassenbuchung", "erfasst_von", "erstellt_am")

    def has_delete_permission(self, request, obj=None):
        # Zahlungen werden nie gelöscht – Korrektur erfolgt per Storno-Gegenbuchung.
        return False


@admin.register(DunningLetter)
class DunningLetterAdmin(admin.ModelAdmin):
    list_display = ("fee", "stufe", "datum", "gebuehr")
    list_filter = ("stufe",)

    def has_delete_permission(self, request, obj=None):
        return False
