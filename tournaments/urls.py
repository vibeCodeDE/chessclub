from django.urls import path

from . import views

app_name = "tournaments"

urlpatterns = [
    # öffentlich
    path("turniere/", views.public_list, name="public_list"),
    path("turniere/<int:pk>/", views.public_detail, name="public_detail"),
    # Verwaltung
    path("turniere/verwalten/", views.manage_list, name="manage_list"),
    path("turniere/verwalten/neu/", views.manage_create, name="manage_create"),
    path("turniere/verwalten/<int:pk>/", views.manage_detail, name="manage_detail"),
    path("turniere/verwalten/<int:pk>/bearbeiten/", views.manage_update, name="manage_update"),
    path("turniere/verwalten/<int:pk>/loeschen/", views.manage_delete, name="manage_delete"),
    path("turniere/verwalten/<int:pk>/teilnehmer/", views.participant_create, name="participant_create"),
    path(
        "turniere/verwalten/teilnehmer/<int:pk>/startgeld/",
        views.participant_toggle_startgeld,
        name="participant_toggle_startgeld",
    ),
    path("turniere/verwalten/teilnehmer/<int:pk>/loeschen/", views.participant_delete, name="participant_delete"),
    path("turniere/verwalten/<int:pk>/runde/", views.round_generate, name="round_generate"),
    path("turniere/verwalten/<int:pk>/runde/<int:nummer>/loeschen/", views.round_delete, name="round_delete"),
    path("turniere/verwalten/paarung/<int:pk>/ergebnis/", views.pairing_result, name="pairing_result"),
    path("turniere/verwalten/<int:pk>/abschluss/", views.tournament_finish, name="tournament_finish"),
    path("turniere/verwalten/<int:pk>/export.csv", views.export_csv, name="export_csv"),
    path("turniere/verwalten/<int:pk>/druck/", views.print_results, name="print_results"),
]
