from django.urls import path

from . import views

app_name = "dues"

urlpatterns = [
    path("beitraege/", views.posten_liste, name="posten_liste"),
    path("beitraege/lauf/", views.beitragslauf, name="beitragslauf"),
    path("beitraege/zahlungen/", views.zahlungsliste, name="zahlungsliste"),
    path("beitraege/zahlungen/buchen/", views.zahlung_buchen, name="zahlung_buchen"),
    path(
        "beitraege/zahlungen/<int:pk>/storno/",
        views.zahlung_stornieren,
        name="zahlung_stornieren",
    ),
    path("beitraege/mandate/", views.mandat_anlegen, name="mandat_anlegen"),
    path(
        "beitraege/mandate/<int:pk>/status/",
        views.mandat_status,
        name="mandat_status",
    ),
    path("beitraege/mahnungen/", views.mahnliste, name="mahnliste"),
    path(
        "beitraege/mahnungen/<int:pk>/setzen/",
        views.mahnung_setzen,
        name="mahnung_setzen",
    ),
    path("beitraege/export.csv", views.beitraege_export, name="beitraege_export"),
]
