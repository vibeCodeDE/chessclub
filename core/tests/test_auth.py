from django.contrib.auth.models import User
from django.test import TestCase


class AuthFlowTests(TestCase):
    def test_login_page_renders(self):
        response = self.client.get("/anmelden/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")

    def test_login_with_valid_credentials(self):
        User.objects.create_user("klaus", password="sicheres-passwort-1")
        response = self.client.post(
            "/anmelden/",
            {"username": "klaus", "password": "sicheres-passwort-1"},
        )
        self.assertEqual(response.status_code, 302)
        # LOGIN_REDIRECT_URL zeigt auf das rollenabhängige Dashboard
        self.assertEqual(response.url, "/dashboard/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_requires_post_and_works(self):
        User.objects.create_user("klaus", password="sicheres-passwort-1")
        self.client.login(username="klaus", password="sicheres-passwort-1")
        response = self.client.get("/abmelden/")
        self.assertEqual(response.status_code, 405)
        response = self.client.post("/abmelden/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
