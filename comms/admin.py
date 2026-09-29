from django.contrib import admin

from .models import MailLog, NewsPost


@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ("titel", "kategorie", "veroeffentlicht", "veroeffentlicht_am", "autor")
    list_filter = ("veroeffentlicht", "kategorie")
    search_fields = ("titel", "text")
    prepopulated_fields = {}


@admin.register(MailLog)
class MailLogAdmin(admin.ModelAdmin):
    list_display = ("erstellt_am", "betreff", "zielgruppe", "anzahl_empfaenger", "anzahl_uebersprungen", "status", "erstellt_von")
    list_filter = ("status", "zielgruppe")
    date_hierarchy = "erstellt_am"
    readonly_fields = [f.name for f in MailLog._meta.fields]

    def has_add_permission(self, request):
        return False
