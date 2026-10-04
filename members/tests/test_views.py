from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase

from core.models import AuditLog
from members.models import Member


def make_user(username, group_name=None):
    user = User.objects.create_user(username, password="x")
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


def make_member(vorname, nachname, **kwargs):
    defaults = {"eintrittsdatum": date(2020, 1, 15)}
    defaults.update(kwargs)
    return Member.objects.create(vorname=vorname, nachname=nachname, **defaults)


class MemberListAccessTests(TestCase):
    def test_list_requires_login(self):
        response = self.client.get("/mitglieder/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_plain_member_is_forbidden(self):
        make_user("p1", "mitglied")
        self.client.login(username="p1", password="x")
        response = self.client.get("/mitglieder/")
        self.assertEqual(response.status_code, 403)

    def test_kapitaen_is_forbidden(self):
        make_user("k1", "kapitaen")
        self.client.login(username="k1", password="x")
        response = self.client.get("/mitglieder/")
        self.assertEqual(response.status_code, 403)


class MemberListTests(TestCase):
    def setUp(self):
        make_user("vorstand", "admin")
        self.client.login(username="vorstand", password="x")

    def test_lists_all_members(self):
        make_member("Anna", "Meier")
        make_member("Bernd", "Schmidt")
        response = self.client.get("/mitglieder/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meier")
        self.assertContains(response, "Schmidt")

    def test_filter_by_status(self):
        make_member("Anna", "Meier")
        make_member("Bernd", "Schmidt", status=Member.Status.PASSIV)
        response = self.client.get("/mitglieder/", {"status": "passiv"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Schmidt")
        self.assertNotContains(response, "Meier")

    def test_filter_by_kategorie_keine(self):
        from dues.models import FeeCategory
        kat = FeeCategory.objects.create(name="Jugend")
        make_member("MitgliedMitKat", "HatKategorie", beitragskategorie=kat)
        make_member("MitgliedOhneKat", "OhneKategorie", beitragskategorie=None)

        response = self.client.get("/mitglieder/", {"kategorie": "keine"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OhneKategorie")
        self.assertNotContains(response, "HatKategorie")

    def test_search_matches_name_and_email(self):
        make_member("Anna", "Meier", email="anna@example.org")
        make_member("Bernd", "Schmidt", email="bernd@example.org")

        response = self.client.get("/mitglieder/", {"q": "schmidt"})
        self.assertContains(response, "Schmidt")
        self.assertNotContains(response, "Meier")

        response = self.client.get("/mitglieder/", {"q": "anna@example.org"})
        self.assertContains(response, "Anna")
        self.assertNotContains(response, "Schmidt")

    def test_invalid_status_param_is_ignored(self):
        make_member("Anna", "Meier")
        response = self.client.get("/mitglieder/", {"status": "quatsch"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meier")

    def test_list_erzeugt_keinen_audit_eintrag(self):
        """PRD N1.5: Listenansichten werden nicht als Zugriff protokolliert."""
        make_member("Anna", "Meier")
        make_member("Bernd", "Schmidt")
        AuditLog.objects.all().delete()
        response = self.client.get("/mitglieder/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            AuditLog.objects.filter(aktion="Mitgliedsakte eingesehen").count(), 0
        )

    def test_nav_shows_members_link_for_admin(self):
        response = self.client.get("/dashboard/")
        self.assertContains(response, 'href="/mitglieder/"')

    def test_nav_hides_members_link_for_member(self):
        self.client.logout()
        make_user("p1", "mitglied")
        self.client.login(username="p1", password="x")
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, 'href="/mitglieder/"')


class MemberDetailTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.login(username="vorstand", password="x")

    def test_detail_requires_login(self):
        self.client.logout()
        member = make_member("Anna", "Meier")
        response = self.client.get(f"/mitglieder/{member.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_detail_is_forbidden_for_plain_member(self):
        """Negativtest: Rolle 'mitglied' darf Detailseite nicht öffnen (403), kein Audit-Log."""
        member = make_member("Anna", "Meier")
        self.client.logout()
        make_user("p1", "mitglied")
        self.client.login(username="p1", password="x")
        AuditLog.objects.all().delete()
        response = self.client.get(f"/mitglieder/{member.pk}/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_detail_is_forbidden_for_kapitaen(self):
        """Negativtest: Rolle 'kapitaen' darf Detailseite nicht öffnen (403), kein Audit-Log."""
        member = make_member("Anna", "Meier")
        self.client.logout()
        make_user("k1", "kapitaen")
        self.client.login(username="k1", password="x")
        AuditLog.objects.all().delete()
        response = self.client.get(f"/mitglieder/{member.pk}/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_detail_erzeugt_audit_eintrag(self):
        """PRD N1.5: Aufruf der Detailansicht protokolliert Wer, Wann und welches Mitglied."""
        member = make_member("Anna", "Meier")
        AuditLog.objects.all().delete()
        response = self.client.get(f"/mitglieder/{member.pk}/")
        self.assertEqual(response.status_code, 200)
        eintrag = AuditLog.objects.filter(aktion="Mitgliedsakte eingesehen").first()
        self.assertIsNotNone(eintrag)
        self.assertEqual(eintrag.benutzer, self.admin)
        self.assertEqual(eintrag.member, member)
        self.assertIn(str(member), eintrag.text)

    def test_detail_shows_data_and_status_history(self):
        member = make_member("Anna", "Meier", email="anna@example.org", telefon="030 123456")
        member.status = Member.Status.PASSIV
        member.save()

        response = self.client.get(f"/mitglieder/{member.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anna")
        self.assertContains(response, "anna@example.org")
        self.assertContains(response, "030 123456")
        self.assertContains(response, "Passiv")
        self.assertContains(response, "Statusverlauf")

    def test_unknown_member_returns_404(self):
        response = self.client.get("/mitglieder/999999/")
        self.assertEqual(response.status_code, 404)


class MemberExportTests(TestCase):
    def test_export_requires_login(self):
        response = self.client.get("/mitglieder/export.csv")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_export_is_forbidden_for_plain_member(self):
        make_user("p1", "mitglied")
        self.client.login(username="p1", password="x")
        response = self.client.get("/mitglieder/export.csv")
        self.assertEqual(response.status_code, 403)

    def test_export_contains_all_members_as_csv(self):
        make_user("vorstand", "admin")
        self.client.login(username="vorstand", password="x")
        make_member("Anna", "Meier", email="anna@example.org")
        make_member("Bernd", "Schmidt")

        response = self.client.get("/mitglieder/export.csv")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        content = response.content.decode("utf-8")
        lines = content.strip().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn("Nachname;Vorname", lines[0])
        self.assertIn("Meier;Anna;;anna@example.org", lines[1])
        self.assertIn("Schmidt;Bernd;", lines[2])

    def test_export_respects_active_filter(self):
        make_user("vorstand", "admin")
        self.client.login(username="vorstand", password="x")
        make_member("Anna", "Meier")
        make_member("Bernd", "Schmidt", status=Member.Status.PASSIV)

        response = self.client.get("/mitglieder/export.csv", {"status": "passiv"})
        content = response.content.decode("utf-8")
        self.assertIn("Schmidt", content)
        self.assertNotIn("Meier", content)
