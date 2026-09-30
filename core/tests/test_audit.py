from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase

from core.models import AuditLog
from members.models import Member


def make_admin(username="vorstand"):
    user = User.objects.create_superuser(username, f"{username}@example.org", "x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


def make_member(**kwargs):
    defaults = {
        "vorname": "Anna",
        "nachname": "Meier",
        "eintrittsdatum": date(2020, 1, 15),
        "email": "anna@example.org",
        "telefon": "030 123456",
    }
    defaults.update(kwargs)
    return Member.objects.create(**defaults)


def formdaten(**aenderungen):
    daten = {
        "user": "",
        "vorname": "Anna",
        "nachname": "Meier",
        "geburtsdatum": "",
        "strasse": "",
        "plz": "",
        "ort": "",
        "email": "anna@example.org",
        "telefon": "030 123456",
        "eintrittsdatum": "15.01.2020",
        "austrittsdatum": "",
        "status": "aktiv",
        "beitragskategorie": "",
        "email_opt_in": "on",
        "status_history-TOTAL_FORMS": "0",
        "status_history-INITIAL_FORMS": "0",
    }
    daten.update(aenderungen)
    return daten


class StammdatenAuditTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.member = make_member()
        self.client.force_login(self.admin)
        self.url = f"/admin/members/member/{self.member.pk}/change/"

    def change(self, **aenderungen):
        return self.client.post(self.url, formdaten(**aenderungen))

    def test_admin_anderung_wird_mit_alt_neu_protokolliert(self):
        response = self.change(email="neu@example.org")

        self.assertRedirects(response, "/admin/members/member/")
        eintrag = AuditLog.objects.get(aktion="Stammdaten geändert")
        self.assertEqual(eintrag.benutzer, self.admin)
        self.assertEqual(eintrag.member, self.member)
        self.assertEqual(eintrag.feld, "email")
        self.assertEqual(eintrag.alt_wert, "anna@example.org")
        self.assertEqual(eintrag.neu_wert, "neu@example.org")

    def test_statuswechsel_wird_protokolliert(self):
        self.change(status="passiv")

        eintrag = AuditLog.objects.get(aktion="Stammdaten geändert")
        self.assertEqual(eintrag.feld, "status")
        self.assertEqual(eintrag.alt_wert, "aktiv")
        self.assertEqual(eintrag.neu_wert, "passiv")

    def test_unchanged_save_wird_nicht_protokolliert(self):
        self.change()

        self.assertEqual(
            AuditLog.objects.filter(aktion="Stammdaten geändert").count(), 0
        )

    def test_anlage_wird_nicht_protokolliert(self):
        self.assertEqual(
            AuditLog.objects.filter(aktion="Stammdaten geändert").count(), 0
        )

    def test_langer_wert_wird_vollständig_protokolliert(self):
        # Regression: alt_wert/neu_wert waren CharField(max_length=200),
        # Member.email erlaubt aber 254 Zeichen – auf Postgres ließ ein
        # langer Wert den Save am Audit-Signal scheitern („value too long").
        lange_email = "l" * 50 + "@" + ".".join(c * 50 for c in "abcd")
        self.assertGreater(len(lange_email), 200)

        response = self.change(email=lange_email)

        self.assertRedirects(response, "/admin/members/member/")
        self.member.refresh_from_db()
        self.assertEqual(self.member.email, lange_email)
        eintrag = AuditLog.objects.get(aktion="Stammdaten geändert")
        self.assertEqual(eintrag.neu_wert, lange_email)


class LoginAuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("l1", "l1@example.org", "x")

    def test_login_wird_protokolliert(self):
        self.assertTrue(self.client.login(username="l1", password="x"))

        eintrag = AuditLog.objects.get(aktion="Anmeldung")
        self.assertEqual(eintrag.benutzer, self.user)
        self.assertIn("IP:", eintrag.text)

    def test_logout_wird_protokolliert(self):
        self.client.login(username="l1", password="x")

        response = self.client.post("/abmelden/")

        self.assertRedirects(response, "/")
        eintrag = AuditLog.objects.get(aktion="Abmeldung")
        self.assertEqual(eintrag.benutzer, self.user)

    def test_abgelehnter_login_wird_protokolliert(self):
        self.assertFalse(self.client.login(username="l1", password="falsch"))

        eintrag = AuditLog.objects.get(aktion="Anmeldung abgelehnt")
        self.assertIsNone(eintrag.benutzer)
        self.assertIn("l1", eintrag.text)


class AuditLogAdminTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.member = make_member()
        self.eintrag = AuditLog.objects.create(
            benutzer=self.admin,
            aktion="Anmeldung",
            text="IP: 127.0.0.1",
            member=self.member,
        )

    def test_changelist_zeigt_eintraege(self):
        self.client.force_login(self.admin)

        response = self.client.get("/admin/core/auditlog/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anmeldung")
        self.assertContains(response, "Meier")

    def test_eintraege_sind_nicht_bearbeitbar(self):
        self.client.force_login(self.admin)
        anzahl = AuditLog.objects.count()

        response = self.client.post(f"/admin/core/auditlog/{self.eintrag.pk}/change/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(AuditLog.objects.count(), anzahl)

    def test_kein_anlegen_von_eintraegen(self):
        self.client.force_login(self.admin)
        anzahl = AuditLog.objects.count()

        response = self.client.get("/admin/core/auditlog/add/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(AuditLog.objects.count(), anzahl)

    def test_nicht_staff_erreicht_kein_auditlog(self):
        User.objects.create_user("p1", "p1@example.org", "x")
        self.client.login(username="p1", password="x")

        response = self.client.get("/admin/core/auditlog/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
