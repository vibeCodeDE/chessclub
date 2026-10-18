from django.contrib import admin

from .models import LeagueCalendarFeed, LeagueMatch, LineupEntry, Season, Team


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "startdatum", "enddatum", "status", "ist_aktiv", "anzahl_teams", "anzahl_spiele")
    list_filter = ("status", "ist_aktiv")
    search_fields = ("name", "notizen")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("erstellt_am", "aktualisiert_am")


class LineupInline(admin.TabularInline):
    model = LineupEntry
    extra = 0
    fields = ("brett", "member", "ersatz_name", "gegner_name", "ergebnis")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "saison", "liga", "altersklasse", "kapitaen", "aktiv", "ical_token")
    list_filter = ("saison", "altersklasse", "aktiv")
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

