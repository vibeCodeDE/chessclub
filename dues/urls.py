from django.urls import path

from . import views

app_name = "dues"

urlpatterns = [
    path("beitraege/", views.overview, name="overview"),
    path("beitraege/lauf/", views.run_beitragslauf, name="run_lauf"),
    path("beitraege/export.csv", views.export, name="export"),
    path("beitraege/kategorien/", views.category_list, name="category_list"),
    path("beitraege/kategorien/<int:pk>/bearbeiten/", views.category_update, name="category_update"),
    path("beitraege/kategorien/<int:pk>/status/", views.category_toggle, name="category_toggle"),
    path("beitraege/kategorien/<int:pk>/loeschen/", views.category_delete, name="category_delete"),
    path("beitraege/mandate/", views.mandate_list, name="mandate_list"),
    path("beitraege/mandate/neu/", views.mandate_create, name="mandate_create"),
    path("beitraege/mandate/<int:pk>/bearbeiten/", views.mandate_update, name="mandate_update"),
    path("beitraege/mahnwesen/", views.dunning_list, name="dunning_list"),
    path("beitraege/mahnwesen/<int:pk>/mahnung/", views.dunning_create, name="dunning_create"),
    path("beitraege/mahnwesen/<int:pk>/brief/", views.dunning_letter, name="dunning_letter"),
    path("beitraege/posten/<int:pk>/", views.fee_detail, name="fee_detail"),
    path("beitraege/posten/<int:pk>/zahlung/", views.payment_create, name="payment_create"),
    path("beitraege/zahlung/<int:pk>/storno/", views.payment_storno, name="payment_storno"),
    path("mein-beitragskonto/", views.mein_konto, name="mein_konto"),
]
