from django.urls import path

from . import views

app_name = "cashbook"

urlpatterns = [
    path("kasse/", views.entry_list, name="entry_list"),
    path("kasse/neu/", views.entry_create, name="entry_create"),
    path("kasse/<int:pk>/bearbeiten/", views.entry_update, name="entry_update"),
    path("kasse/<int:pk>/storno/", views.entry_storno, name="entry_storno"),
    path("kasse/<int:pk>/loeschen/", views.entry_delete, name="entry_delete"),
    path("kasse/jahresabschluss/", views.jahresabschluss_view, name="jahresabschluss"),
    path("kasse/export.csv", views.export, name="export"),
]
