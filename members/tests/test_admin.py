from datetime import date

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from members.admin import MemberAdmin
from members.models import Member


def make_member(vorname, nachname, **kwargs):
    defaults = {"eintrittsdatum": date(2020, 1, 15)}
    defaults.update(kwargs)
    return Member.objects.create(vorname=vorname, nachname=nachname, **defaults)


class MemberAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser("root", password="x")
        self.client.login(username="root", password="x")

    def test_delete_permission_is_disabled(self):
        request = RequestFactory().get("/")
        request.user = self.admin_user
        self.assertFalse(MemberAdmin(Member, AdminSite()).has_delete_permission(request))

    def test_admin_can_create_member(self):
        response = self.client.post(
            "/admin/members/member/add/",
            {
                "vorname": "Anna",
                "nachname": "Meier",
                "geburtsdatum": "",
                "strasse": "",
                "plz": "",
                "ort": "Berlin",
                "email": "anna@example.org",
                "telefon": "",
                "eintrittsdatum": "15.01.2020",
                "austrittsdatum": "",
                "status": "aktiv",
                "user": "",
                "status_history-TOTAL_FORMS": "0",
                "status_history-INITIAL_FORMS": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Member.objects.filter(nachname="Meier", vorname="Anna").exists())

    def test_changelist_search_finds_by_name(self):
        make_member("Anna", "Meier")
        make_member("Bernd", "Schmidt")
        response = self.client.get("/admin/members/member/", {"q": "Meier"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meier")
        self.assertNotContains(response, "Schmidt")

    def test_changelist_filters_by_status(self):
        make_member("Anna", "Meier")
        make_member("Bernd", "Schmidt", status=Member.Status.PASSIV)
        response = self.client.get("/admin/members/member/", {"status": "passiv"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Schmidt")
        self.assertNotContains(response, "Meier")

    def test_status_change_through_admin_is_historized_with_user(self):
        member = make_member("Anna", "Meier")
        response = self.client.post(
            f"/admin/members/member/{member.pk}/change/",
            {
                "vorname": "Anna",
                "nachname": "Meier",
                "geburtsdatum": "",
                "strasse": "",
                "plz": "",
                "ort": "",
                "email": "",
                "telefon": "",
                "eintrittsdatum": "15.01.2020",
                "austrittsdatum": "01.06.2025",
                "status": "ausgetreten",
                "user": "",
                "status_history-TOTAL_FORMS": "0",
                "status_history-INITIAL_FORMS": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        member.refresh_from_db()
        self.assertEqual(member.status, Member.Status.AUSGETRETEN)
        change = member.status_history.get()
        self.assertEqual(change.von, Member.Status.AKTIV)
        self.assertEqual(change.nach, Member.Status.AUSGETRETEN)
        self.assertEqual(change.geaendert_von, self.admin_user)
