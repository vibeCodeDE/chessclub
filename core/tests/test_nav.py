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
        # Navigation der App-Shell liegt im Dashboard (öffentliche Seite ist "/")
        response = self.client.get("/dashboard/")
        content = response.content.decode()
        self.assertEqual(response.context["user_role"], "mitglied")
        self.assertIn("Profil", content)
        self.assertNotIn("Verwaltung", content)
        self.assertNotIn("Anmelden", content)

    def test_kapitaen_sees_profile_but_no_admin(self):
        make_user("kapit1", "kapitaen")
        self.client.login(username="kapit1", password="x")
        response = self.client.get("/dashboard/")
        content = response.content.decode()
        self.assertEqual(response.context["user_role"], "kapitaen")
        self.assertIn("Profil", content)
        self.assertNotIn("Verwaltung", content)
        self.assertNotIn("Anmelden", content)
        self.assertIn("Abmelden", content)

    def test_admin_sees_verwaltung(self):
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get("/dashboard/")
        content = response.content.decode()
        self.assertEqual(response.context["user_role"], "admin")
        self.assertIn("Verwaltung", content)
        self.assertNotIn("Anmelden", content)

    def test_admin_sees_beitraege(self):
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get("/dashboard/")
        self.assertContains(response, 'href="/beitraege/"')
        self.assertContains(response, "Beiträge")

    def test_member_sees_no_beitraege(self):
        """Negativtest: der Beitrags-Nav-Eintrag bleibt beim Mitglied weg."""
        make_user("mitglied1", "mitglied")
        self.client.login(username="mitglied1", password="x")
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, 'href="/beitraege/"')

    def test_admin_sees_mahnwesen(self):
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get("/dashboard/")
        self.assertContains(response, 'href="/beitraege/mahnwesen/"')

    def test_member_sees_no_mahnwesen(self):
        """Negativtest: das Mahnwesen bleibt Vorstandssache (PRD §3.8)."""
        make_user("mitglied1", "mitglied")
        self.client.login(username="mitglied1", password="x")
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, 'href="/beitraege/mahnwesen/"')

    def test_admin_sees_kassenbuch_und_mandate(self):
        """Die Finanzsektion der Navigation ist vollständig (PRD M2.1–M2.6)."""
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get("/dashboard/")
        for pfad in (
            "/beitraege/",
            "/beitraege/kategorien/",
            "/beitraege/mandate/",
            "/beitraege/mahnwesen/",
            "/kasse/",
        ):
            self.assertContains(response, f'href="{pfad}"')

    def test_kapitaen_sees_keine_finanzsektion(self):
        """Negativtest: Kapitän bekommt weder Beiträge noch Mahnwesen (PRD §3.8)."""
        make_user("kapit1", "kapitaen")
        self.client.login(username="kapit1", password="x")
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, 'href="/beitraege/"')
        self.assertNotContains(response, 'href="/beitraege/mahnwesen/"')
        self.assertNotContains(response, 'href="/kasse/"')
