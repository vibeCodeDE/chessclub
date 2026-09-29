"""Ankündigungen: Entwurf, Veröffentlichung und öffentliche Sichtbarkeit."""

import json
from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase

from comms.models import NewsPost


def make_admin(username="vorstand"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


class NewsWorkflowTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.force_login(self.admin)

    def test_entwurf_ist_nicht_oeffentlich(self):
        NewsPost.objects.create(titel="Intern", text="Noch nicht fertig", veroeffentlicht=False)
        response = self.client.get("/aktuelles/")
        self.assertNotContains(response, "Intern")
        self.assertNotContains(self.client.get("/"), "Intern")

    def test_veroeffentlichen_setzt_zeitstempel(self):
        post = NewsPost.objects.create(titel="Neuigkeit", text="Text", veroeffentlicht=False)
        response = self.client.post(
            f"/ankuendigungen/{post.pk}/veroeffentlichen/", HTTP_ACCEPT="application/json"
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertTrue(daten["checked"])
        post.refresh_from_db()
        self.assertTrue(post.veroeffentlicht)
        self.assertIsNotNone(post.veroeffentlicht_am)

        self.assertContains(self.client.get("/"), "Neuigkeit")
        self.assertContains(self.client.get("/aktuelles/"), "Neuigkeit")

    def test_zurueckziehen_nimmt_von_startseite(self):
        post = NewsPost.objects.create(titel="Kurz sichtbar", text="Text")
        post.veroeffentlichen()
        self.client.post(
            f"/ankuendigungen/{post.pk}/veroeffentlichen/", HTTP_ACCEPT="application/json"
        )
        post.refresh_from_db()
        self.assertFalse(post.veroeffentlicht)
        self.assertNotContains(self.client.get("/"), "Kurz sichtbar")

    def test_create_ueber_formular_mit_autor(self):
        response = self.client.post(
            "/ankuendigungen/neu/",
            {"titel": "Neuer Bericht", "kategorie": "Bericht", "text": "Inhalt", "veroeffentlicht": "on"},
        )
        self.assertRedirects(response, "/ankuendigungen/")
        post = NewsPost.objects.get(titel="Neuer Bericht")
        self.assertEqual(post.autor, self.admin)
        self.assertTrue(post.veroeffentlicht)

    def test_loeschen_ueber_ajax(self):
        post = NewsPost.objects.create(titel="Wegwerf", text="x")
        response = self.client.post(
            f"/ankuendigungen/{post.pk}/loeschen/", HTTP_ACCEPT="application/json"
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertFalse(NewsPost.objects.filter(pk=post.pk).exists())

    def test_detailseite_nur_fuer_veroeffentlichte(self):
        entwurf = NewsPost.objects.create(titel="Entwurf", text="x")
        self.assertEqual(self.client.get(f"/aktuelles/{entwurf.pk}/").status_code, 404)
        entwurf.veroeffentlichen()
        self.assertEqual(self.client.get(f"/aktuelles/{entwurf.pk}/").status_code, 200)

    def test_mitglieder_duerfen_nicht_verwalten(self):
        user = User.objects.create_user("p1", password="x")
        group, _ = Group.objects.get_or_create(name="mitglied")
        user.groups.add(group)
        self.client.force_login(user)
        self.assertEqual(self.client.get("/ankuendigungen/").status_code, 403)

    def test_liste_filter_bearbeiten_und_fehlerpfade(self):
        entwurf = NewsPost.objects.create(titel="Entwurf 1", text="x", veroeffentlicht=False)
        oeffentlich = NewsPost.objects.create(titel="Live 1", text="y", veroeffentlicht=True)

        r_entwurf = self.client.get("/ankuendigungen/?status=entwurf")
        self.assertContains(r_entwurf, "Entwurf 1")
        self.assertNotContains(r_entwurf, "Live 1")

        r_live = self.client.get("/ankuendigungen/?status=veroeffentlicht")
        self.assertContains(r_live, "Live 1")
        self.assertNotContains(r_live, "Entwurf 1")

        # Formular GET + AJAX-Fehler bei leerem Titel
        self.assertEqual(self.client.get("/ankuendigungen/neu/").status_code, 200)
        err_create = self.client.post(
            "/ankuendigungen/neu/", {"titel": "", "text": ""}, HTTP_ACCEPT="application/json"
        )
        self.assertFalse(json.loads(err_create.content)["ok"])

        # Bearbeiten GET + POST (regulär und AJAX) + AJAX-Fehler
        self.assertEqual(self.client.get(f"/ankuendigungen/{entwurf.pk}/bearbeiten/").status_code, 200)
        upd_html = self.client.post(
            f"/ankuendigungen/{entwurf.pk}/bearbeiten/",
            {"titel": "Jetzt veröffentlicht", "kategorie": "Verein", "text": "Inhalt", "veroeffentlicht": "on"},
        )
        self.assertRedirects(upd_html, "/ankuendigungen/")
        entwurf.refresh_from_db()
        self.assertTrue(entwurf.veroeffentlicht)
        self.assertIsNotNone(entwurf.veroeffentlicht_am)

        upd_ajax = self.client.post(
            f"/ankuendigungen/{oeffentlich.pk}/bearbeiten/",
            {"titel": "Live aktualisiert", "kategorie": "Verein", "text": "Neu"},
            HTTP_ACCEPT="application/json",
        )
        self.assertTrue(json.loads(upd_ajax.content)["ok"])

        err_upd = self.client.post(
            f"/ankuendigungen/{oeffentlich.pk}/bearbeiten/",
            {"titel": "", "text": ""},
            HTTP_ACCEPT="application/json",
        )
        self.assertFalse(json.loads(err_upd.content)["ok"])
