from django.contrib.auth.models import User
from django.test import TestCase


class ProfilTests(TestCase):
    def test_profil_requires_login(self):
        response = self.client.get("/profil/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_profil_accessible_for_logged_in_member(self):
        User.objects.create_user("p1", password="x")
        self.client.login(username="p1", password="x")
        response = self.client.get("/profil/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profil")
