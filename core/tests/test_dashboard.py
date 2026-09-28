from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase

from members.models import ChangeRequest, Member


def make_user(username, group_name=None):
    user = User.objects.create_user(username, password="x")
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


def make_member(user=None):
    return Member.objects.create(
        vorname="Anna",
        nachname="Meier",
        eintrittsdatum=date(2020, 1, 15),
        email="anna@example.org",
        user=user,
    )


class DashboardTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin1", "admin")

    def login_admin(self):
        self.client.login(username="admin1", password="x")

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)
        self.assertIn("next=/dashboard/", response.url)

    def test_member_is_forbidden(self):
        make_user("mitglied1", "mitglied")
        self.client.login(username="mitglied1", password="x")
        self.assertEqual(self.client.get("/dashboard/").status_code, 403)

    def test_kapitaen_is_forbidden(self):
        make_user("kapit1", "kapitaen")
        self.client.login(username="kapit1", password="x")
        self.assertEqual(self.client.get("/dashboard/").status_code, 403)

    def test_admin_sees_all_tiles(self):
        self.login_admin()
        response = self.client.get("/dashboard/")
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        for titel in (
            "Offene Beiträge",
            "Anstehende Termine",
            "Offene Änderungswünsche",
            "Letzte Anmeldungen",
        ):
            self.assertIn(titel, content)

    def test_fee_tile_is_placeholder_until_beitragslauf(self):
        self.login_admin()
        response = self.client.get("/dashboard/")
        self.assertContains(response, "Verfügbar nach dem Beitragslauf.")

    def test_change_request_tile_shows_open_count(self):
        member = make_member()
        ChangeRequest.objects.create(member=member, feld="telefon", wunschwert="1")
        ChangeRequest.objects.create(
            member=member,
            feld="plz",
            wunschwert="2",
            status=ChangeRequest.Status.FREIGEGEBEN,
        )
        self.login_admin()

        response = self.client.get("/dashboard/")

        tile = next(t for t in response.context["tiles"] if t["key"] == "wuensche")
        self.assertEqual(tile["wert"], 1)
        self.assertFalse(tile["placeholder"])

    def test_zero_open_requests_is_shown_without_error(self):
        self.login_admin()
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        tile = next(t for t in response.context["tiles"] if t["key"] == "wuensche")
        self.assertEqual(tile["wert"], 0)

    def test_admin_nav_contains_dashboard_link(self):
        self.login_admin()
        content = self.client.get("/").content.decode()
        self.assertIn("Dashboard", content)

    def test_member_nav_has_no_dashboard_link(self):
        make_user("mitglied2", "mitglied")
        self.client.login(username="mitglied2", password="x")
        content = self.client.get("/").content.decode()
        self.assertNotIn("Dashboard", content)
