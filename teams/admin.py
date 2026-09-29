from django.contrib import admin

from .models import LeagueMatch, LineupEntry, Team


class LineupInline(admin.TabularInline):
    model = LineupEntry
    extra = 0
    fields = ("brett", "member", "ersatz_name", "gegner_name", "ergebnis")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "liga", "altersklasse", "kapitaen", "aktiv")
    list_filter = ("altersklasse", "aktiv")
    search_fields = ("name", "liga")


@admin.register(LeagueMatch)
class LeagueMatchAdmin(admin.ModelAdmin):
    list_display = ("team", "datum", "gegner", "heimspiel", "status", "brettpunkte_anzeige")
    list_filter = ("team", "status")
    search_fields = ("gegner",)
    inlines = [LineupInline]
