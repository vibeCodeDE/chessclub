from django.urls import path

from . import views

app_name = "dues"

urlpatterns = [
    path("beitraege/", views.posten_liste, name="posten_liste"),
    path("beitraege/lauf/", views.beitragslauf, name="beitragslauf"),
]
