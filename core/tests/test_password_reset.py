from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase


class PasswordResetTests(TestCase):
    def test_reset_form_renders(self):
        response = self.client.get("/passwort/aendern/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")

    def test_reset_sends_email_with_link(self):
        User.objects.create_user("u1", email="u1@example.de", password="x")
        response = self.client.post(
            "/passwort/aendern/", {"email": "u1@example.de"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/passwort/aendern/", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["u1@example.de"])

    def test_reset_for_unknown_email_sends_nothing(self):
        response = self.client.post(
            "/passwort/aendern/", {"email": "unbekannt@example.de"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
