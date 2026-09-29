from django.contrib import admin

from .models import Pairing, Participant, Tournament, TournamentRound


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    fields = ("name", "verein", "twz", "startgeld_bezahlt")


class PairingInline(admin.TabularInline):
    model = Pairing
    extra = 0
    fields = ("brett", "weiss", "schwarz", "ergebnis")


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "datum", "format", "status", "oeffentlich", "teilnehmer_anzahl")
    list_filter = ("status", "format", "oeffentlich")
    search_fields = ("name", "ort")
    inlines = [ParticipantInline]


@admin.register(TournamentRound)
class TournamentRoundAdmin(admin.ModelAdmin):
    list_display = ("tournament", "nummer", "offene_partien")
    list_filter = ("tournament",)
    inlines = [PairingInline]
