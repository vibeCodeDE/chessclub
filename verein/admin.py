from django.contrib import admin

from .models import Vereinsdaten


@admin.register(Vereinsdaten)
class VereinsdatenAdmin(admin.ModelAdmin):
    """Die Vereinsdaten werden ausschließlich hier gepflegt (T10)."""

    fields = (
        "name",
        "strasse",
        "plz",
        "ort",
        "telefon",
        "email",
        "kassierer",
        "zahlungshinweis",
        "zahlungsziel",
    )

    def has_add_permission(self, request):
        # Es gibt nur einen Datensatz (pk=1) — ein zweiter wäre bedeutungslos.
        return not Vereinsdaten.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
