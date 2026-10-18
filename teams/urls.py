from django.urls import path

from . import views

app_name = "teams"

urlpatterns = [
    path("mannschaften/", views.team_list, name="team_list"),
    path("mannschaften/neu/", views.team_create, name="team_create"),
    path("mannschaften/<int:pk>/", views.team_detail, name="team_detail"),
    path("mannschaften/<int:pk>/bearbeiten/", views.team_update, name="team_update"),
    path("mannschaften/<int:pk>/loeschen/", views.team_delete, name="team_delete"),
    path("spiele/", views.match_list, name="match_list"),
    path("spiele/neu/", views.match_create, name="match_create"),
    path("spiele/<int:pk>/", views.match_detail, name="match_detail"),
    path("spiele/<int:pk>/drucken/", views.match_print, name="match_print"),
    path("spiele/<int:pk>/bearbeiten/", views.match_update, name="match_update"),
    path("spiele/<int:pk>/loeschen/", views.match_delete, name="match_delete"),
    path("spiele/<int:pk>/brett/<int:brett>/", views.lineup_board_save, name="lineup_board_save"),
    path("spiele/<int:pk>/aufstellung/", views.lineup_save, name="lineup_save"),
    path("ligen/", views.tabelle_list, name="tabelle_list"),
    path("meine-einsaetze/", views.meine_aufstellungen, name="meine_aufstellungen"),
    path("ical/gesamt/token-erneuern/", views.gesamt_renew_ical_token, name="gesamt_renew_ical_token"),
    path("ical/gesamt/<str:token>/", views.ical_feed_gesamt, name="ical_gesamt"),
    path("mannschaften/<int:pk>/ical-token-erneuern/", views.team_renew_ical_token, name="team_renew_ical_token"),
    path("mannschaften/<int:pk>/ical/<str:token>/", views.ical_feed_team, name="ical_team"),
    # Saisonverwaltung (004-saison-verwaltung)
    path("saison/", views.season_list, name="season_list"),
    path("saison/neu/", views.season_create, name="season_create"),
    path("saison/<int:pk>/bearbeiten/", views.season_edit, name="season_edit"),
    path("saison/<int:pk>/aktivieren/", views.season_activate, name="season_activate"),
    path("saison/<int:pk>/abschliessen/", views.season_archive, name="season_archive"),
    path("saison/<int:pk>/reaktivieren/", views.season_reopen, name="season_reopen"),
    path("saison/<int:pk>/loeschen/", views.season_delete, name="season_delete"),
    path("saison/<int:pk>/uebernahme/", views.season_rollover, name="season_rollover"),
]

