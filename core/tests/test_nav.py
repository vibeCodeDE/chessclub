from django.contrib.auth.models import Group, User
from django.test import TestCase


def make_user(username, group_name=None):
    user = User.objects.create_user(username, password="x")
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


class NavTests(TestCase):
    def test_anonymous_sees_login_and_no_admin(self):
        response = self.client.get("/")
        content = response.content.decode()
        self.assertEqual(response.context["user_role"], "gast")
        self.assertIn("Anmelden", content)
        self.assertNotIn("Verwaltung", content)
        self.assertNotIn("Profil", content)

    def test_member_sees_profile_but_no_admin(self):
        make_user("mitglied1", "mitglied")
        self.client.login(username="mitglied1", password="x")
        response = self.client.get("/")
        content = response.content.decode()
        self.assertEqual(response.context["user_role"], "mitglied")
        self.assertIn("Profil", content)
        self.assertNotIn("Verwaltung", content)
        self.assertNotIn("Anmelden", content)

    def test_kapitaen_sees_profile_but_no_admin(self):
        make_user("kapit1", "kapitaen")
        self.client.login(username="kapit1", password="x")
        response = self.client.get("/")
        content = response.content.decode()
        self.assertEqual(response.context["user_role"], "kapitaen")
        self.assertIn("Profil", content)
        self.assertNotIn("Verwaltung", content)
        self.assertNotIn("Anmelden", content)
        self.assertIn("Abmelden", content)

    def test_admin_sees_verwaltung(self):
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get("/")
        content = response.content.decode()
        self.assertEqual(response.context["user_role"], "admin")
        self.assertIn("Verwaltung", content)
        self.assertNotIn("Anmelden", content)
