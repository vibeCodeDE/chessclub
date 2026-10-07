from django.urls import path

from . import views

app_name = "members"

urlpatterns = [
    path("profil/", views.profil, name="profil"),
    path("mitglied-werden/", views.join_info, name="join_info"),
    path("mitglieder/", views.member_list, name="member_list"),
    path("mitglieder/dsb-sync/", views.dsb_sync_view, name="dsb_sync"),
    path("mitglieder/neu/", views.member_create, name="member_create"),
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
    path("mitglieder/<int:pk>/bearbeiten/", views.member_update, name="member_update"),
    path("mitglieder/<int:pk>/status/", views.member_status, name="member_status"),
    path("mitglieder/<int:pk>/austritt/", views.member_delete, name="member_delete"),
]
