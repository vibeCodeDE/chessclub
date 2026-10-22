from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


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

    def test_aktiver_menuepunkt_und_aria_current(self):
        """Exakter Aufruf markiert Menüpunkt mit active/is-active und aria-current="page"."""
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get(reverse("members:member_list"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        # Mitglieder-Link muss aktiv sein und aria-current="page" tragen
        self.assertIn('aria-current="page"', html)
        self.assertIn('class="nav-item nav-link active is-active"', html)

    def test_unterseiten_aktivieren_uebergeordneten_navigationspunkt(self):
        """Unterseiten (z. B. Mitglied anlegen /mitglieder/neu/) aktivieren den Hauptmenüpunkt."""
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get(reverse("members:member_create"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        # Bei /mitglieder/neu/ muss der Link zu /mitglieder/ als aktiv markiert sein
        self.assertIn('href="/mitglieder/" aria-current="page"', html)

    def test_praefix_kollision_waehlt_spezifischsten_navigationspunkt(self):
        """Bei Pfad-Präfixen (z. B. /beitraege/kategorien/ vs /beitraege/) gewinnt der spezifische Link."""
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get(reverse("dues:category_list"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        # Beitragskategorien muss aria-current="page" haben, allgemeine Beiträge nicht
        self.assertIn('href="/beitraege/kategorien/" aria-current="page"', html)
        self.assertNotIn('href="/beitraege/" aria-current="page"', html)

    def test_mobiler_schliessen_button_und_landmarks(self):
        """Sidebar enthält mobilen Schließen-Button und semantisch getrennte ARIA-Landmarks."""
        make_user("admin1", "admin")
        self.client.login(username="admin1", password="x")
        response = self.client.get(reverse("core:dashboard"))
        html = response.content.decode("utf-8")

        # Getrennte Landmark-Beschriftungen
        self.assertIn('<aside class="sidebar" id="sidebar" aria-label="Seitenleiste">', html)
        self.assertIn('<nav class="sidebar-nav main-navigation" aria-label="Hauptnavigation">', html)

        # Mobiler Schließen-Button
        self.assertIn('data-sidebar-close', html)
        self.assertIn('class="icon-btn sidebar-close-btn"', html)
        self.assertIn('aria-label="Navigation schließen"', html)

    def test_oeffentliche_hauptnavigation_mitglied_werden_aktiv(self):
        """Auf /mitglied-werden/ ist der Menüpunkt mit aria-current="page" ausgezeichnet."""
        response = self.client.get(reverse("members:join_info"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('href="/mitglied-werden/" aria-current="page"', html)
