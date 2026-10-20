from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings

from core.models import OnboardingProgress, TwoFactorDevice
from core.roles import ADMIN_GROUP
from core.twofa import code_erzeugen, neues_secret


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

    def test_login_redirect_with_safe_next_url(self):
        """Positivtest: Gültige interne relative next-URL wird angesprungen."""
        User.objects.create_user("klaus", password="sicheres-passwort-1")
        response = self.client.post(
            "/anmelden/?next=/mitglieder/",
            {"username": "klaus", "password": "sicheres-passwort-1"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/mitglieder/")

    def test_negativ_login_rejects_open_redirect_external_url(self):
        """Negativtest CWE-601: Externe Phishing-URL wird abgewiesen und leitet zum Dashboard."""
        User.objects.create_user("klaus", password="sicheres-passwort-1")
        response = self.client.post(
            "/anmelden/?next=https://evil-phishing.com/login",
            {"username": "klaus", "password": "sicheres-passwort-1"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")

    def test_negativ_login_rejects_open_redirect_scheme_relative(self):
        """Negativtest CWE-601: Scheme-relative URL (//evil.com) wird abgewiesen."""
        User.objects.create_user("klaus", password="sicheres-passwort-1")
        response = self.client.post(
            "/anmelden/",
            {
                "username": "klaus",
                "password": "sicheres-passwort-1",
                "next": "//evil-phishing.com/stealdoc",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")

    def test_negativ_login_page_sanitizes_external_next_parameter(self):
        """Negativtest: GET /anmelden/?next=... rendert keine bösartige URL ins Template."""
        response = self.client.get("/anmelden/?next=https://evil-phishing.com/login")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "evil-phishing.com")

    def test_login_page_renders_safe_next_hidden_input(self):
        """Positivtest: GET /anmelden/?next=/mitglieder/ übergibt das sichere next-Ziel ans Formular."""
        response = self.client.get("/anmelden/?next=/mitglieder/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="next" value="/mitglieder/"')

    def test_authenticated_user_with_safe_next_url(self):
        """Bereits angemeldeter Nutzer mit sicherem next wird dorthin weitergeleitet."""
        user = User.objects.create_user("klaus", password="sicheres-passwort-1")
        self.client.force_login(user)
        response = self.client.get("/anmelden/?next=/mitglieder/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/mitglieder/")

    def test_negativ_authenticated_user_rejects_open_redirect(self):
        """Negativtest CWE-601: Bereits angemeldeter Nutzer mit externem next landet im Dashboard."""
        user = User.objects.create_user("klaus", password="sicheres-passwort-1")
        self.client.force_login(user)
        response = self.client.get("/anmelden/?next=https://evil-phishing.com/login")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")


@override_settings(TWOFA_PFLICHT=True)
class TwoFactorOpenRedirectTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("vorstand", password="sicheres-passwort-1")
        group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        self.admin.groups.add(group)
        self.secret = neues_secret()
        TwoFactorDevice.objects.create(user=self.admin, secret=self.secret, bestaetigt=True)
        OnboardingProgress.objects.create(pk=1, ist_abgeschlossen=True)

    def test_two_factor_preserves_safe_next_url(self):
        """Positivtest: Valides next-Ziel übersteht den 2FA-Zwischenschritt."""
        self.client.post(
            "/anmelden/?next=/mitglieder/",
            {"username": "vorstand", "password": "sicheres-passwort-1"},
        )
        self.assertEqual(self.client.session.get("_2fa_next"), "/mitglieder/")
        response = self.client.post(
            "/anmelden/zwei-faktor/",
            {"code": code_erzeugen(self.secret)},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/mitglieder/")

    def test_negativ_two_factor_rejects_open_redirect_url(self):
        """Negativtest CWE-601: Manipuliertes next-Ziel wird vor 2FA bereinigt."""
        self.client.post(
            "/anmelden/?next=https://evil-phishing.com/login",
            {"username": "vorstand", "password": "sicheres-passwort-1"},
        )
        # _2fa_next darf keine Phishing-URL enthalten
        self.assertNotEqual(self.client.session.get("_2fa_next"), "https://evil-phishing.com/login")
        response = self.client.post(
            "/anmelden/zwei-faktor/",
            {"code": code_erzeugen(self.secret)},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")

    def test_negativ_two_factor_rejects_tampered_session_next(self):
        """Negativtest CWE-601: Selbst bei manipulierter Session (_2fa_next) greift die Validierung."""
        session = self.client.session
        session["_2fa_user_id"] = self.admin.pk
        session["_2fa_next"] = "https://evil-phishing.com/takeover"
        session.save()

        response = self.client.post(
            "/anmelden/zwei-faktor/",
            {"code": code_erzeugen(self.secret)},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")
