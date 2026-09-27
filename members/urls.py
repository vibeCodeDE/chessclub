from django.urls import path

from . import views

app_name = "members"

urlpatterns = [
    path("mitglieder/", views.member_list, name="member_list"),
    path("mitglieder/export.csv", views.member_export, name="member_export"),
    path("mitglieder/<int:pk>/", views.member_detail, name="member_detail"),
]
