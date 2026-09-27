from django.urls import path

from . import views

app_name = "members"

urlpatterns = [
    path("profil/", views.profil, name="profil"),
    path("mitglieder/", views.member_list, name="member_list"),
    path("mitglieder/export.csv", views.member_export, name="member_export"),
    path(
        "mitglieder/wuensche/",
        views.change_request_list,
        name="change_request_list",
    ),
    path(
        "mitglieder/wuensche/<int:pk>/freigabe/",
        views.change_request_approve,
        name="change_request_approve",
    ),
    path(
        "mitglieder/wuensche/<int:pk>/ablehnung/",
        views.change_request_reject,
        name="change_request_reject",
    ),
    path("mitglieder/<int:pk>/", views.member_detail, name="member_detail"),
]
