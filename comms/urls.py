from django.urls import path

from . import views

app_name = "comms"

urlpatterns = [
    path("ankuendigungen/", views.news_list, name="news_list"),
    path("ankuendigungen/neu/", views.news_create, name="news_create"),
    path("ankuendigungen/<int:pk>/bearbeiten/", views.news_update, name="news_update"),
    path("ankuendigungen/<int:pk>/loeschen/", views.news_delete, name="news_delete"),
    path("ankuendigungen/<int:pk>/veroeffentlichen/", views.news_toggle, name="news_toggle"),
    path("ankuendigungen/mail/", views.mail_list, name="mail_list"),
]
