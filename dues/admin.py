from django.contrib import admin

from .models import DunningLetter, FeeCategory, MembershipFee, Payment, SepaMandate


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "betrag", "aktiv", "mitglieder_anzahl")
    list_filter = ("aktiv",)
    search_fields = ("name",)


@admin.register(SepaMandate)
class SepaMandateAdmin(admin.ModelAdmin):
    list_display = ("member", "referenz", "iban_kurz", "status", "erteilt_am")
    list_filter = ("status",)
    search_fields = ("member__nachname", "member__vorname", "referenz")


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("betrag", "datum", "art", "notiz")


@admin.register(MembershipFee)
class MembershipFeeAdmin(admin.ModelAdmin):
    list_display = ("member", "jahr", "kategorie_name", "betrag", "status", "mahnstufe")
    list_filter = ("jahr", "status")
    search_fields = ("member__nachname", "member__vorname")
    inlines = [PaymentInline]


@admin.register(DunningLetter)
class DunningLetterAdmin(admin.ModelAdmin):
    list_display = ("fee", "stufe", "datum", "gebuehr")
    list_filter = ("stufe",)
