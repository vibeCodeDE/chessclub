from django.contrib import admin

from .models import LeagueCalendarFeed, LeagueMatch, LineupEntry, Team


class LineupInline(admin.TabularInline):
    model = LineupEntry
    extra = 0
    fields = ("brett", "member", "ersatz_name", "gegner_name", "ergebnis")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "liga", "altersklasse", "kapitaen", "aktiv", "ical_token")
    list_filter = ("altersklasse", "aktiv")
    search_fields = ("name", "liga")
    readonly_fields = ("ical_token",)


@admin.register(LeagueMatch)
class LeagueMatchAdmin(admin.ModelAdmin):
    list_display = ("team", "datum", "gegner", "heimspiel", "status", "brettpunkte_anzeige")
    list_filter = ("team", "status")
    search_fields = ("gegner",)
    inlines = [LineupInline]


@admin.register(LeagueCalendarFeed)
class LeagueCalendarFeedAdmin(admin.ModelAdmin):
    list_display = ("name", "token", "aktualisiert_am")
    readonly_fields = ("token", "aktualisiert_am")

