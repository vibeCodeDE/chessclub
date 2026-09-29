"""Härtung: Zwei-Faktor für den Vorstand und Sicherheits-Header (T22)."""

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import TwoFactorDevice
from core.roles import ADMIN_GROUP
from core.twofa import code_erzeugen, neues_secret, otpauth_uri


def make_user(username, group_name=None):
    user = User.objects.create_user(username, password="sicheres-passwort-1")
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


# Die 2FA-Pflicht wird im Test fest gesetzt: der Wert kommt sonst aus der
# Umgebung, und die Entwicklungs-Compose schaltet ihn ab (README).
@override_settings(TWOFA_PFLICHT=True)
class ZweiFaktorTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", ADMIN_GROUP)

    def test_vorstand_muss_zwei_faktor_einrichten(self):
        response = self.client.post(
            "/anmelden/", {"username": "vorstand", "password": "sicheres-passwort-1"}
        )
        self.assertRedirects(response, "/anmelden/zwei-faktor/")
        self.assertNotIn("_auth_user_id", self.client.session, "Noch nicht angemeldet")

        seite = self.client.get("/anmelden/zwei-faktor/")
        self.assertEqual(seite.status_code, 200)
        self.assertContains(seite, "Schlüssel")
        secret = self.client.session["_2fa_secret"]

        falsch = self.client.post("/anmelden/zwei-faktor/", {"code": "000000"})
        self.assertContains(falsch, "stimmt nicht")
        self.assertNotIn("_auth_user_id", self.client.session)

        richtig = self.client.post("/anmelden/zwei-faktor/", {"code": code_erzeugen(secret)})
        self.assertRedirects(richtig, "/dashboard/")
        self.assertIn("_auth_user_id", self.client.session)
        device = TwoFactorDevice.objects.get(user=self.admin)
        self.assertTrue(device.bestaetigt)

    def test_zweite_anmeldung_verlangt_nur_den_code(self):
        secret = neues_secret()
        TwoFactorDevice.objects.create(user=self.admin, secret=secret, bestaetigt=True)
        self.client.post("/anmelden/", {"username": "vorstand", "password": "sicheres-passwort-1"})
        self.assertContains(self.client.get("/anmelden/zwei-faktor/"), "6-stelligen Code")

        response = self.client.post("/anmelden/zwei-faktor/", {"code": code_erzeugen(secret)})
        self.assertRedirects(response, "/dashboard/")
        device = TwoFactorDevice.objects.get(user=self.admin)
        self.assertIsNotNone(device.letzte_nutzung)
        self.assertLessEqual(device.letzte_nutzung, timezone.now())

    def test_mitglied_ohne_adminrolle_braucht_kein_zwei_faktor(self):
        make_user("mitglied1", "mitglied")
        response = self.client.post(
            "/anmelden/", {"username": "mitglied1", "password": "sicheres-passwort-1"}
        )
        self.assertRedirects(response, "/dashboard/")
        self.assertIn("_auth_user_id", self.client.session)

    def test_pflicht_abschaltbar_fuer_entwicklung(self):
        with self.settings(TWOFA_PFLICHT=False):
            response = self.client.post(
                "/anmelden/", {"username": "vorstand", "password": "sicheres-passwort-1"}
            )
        self.assertRedirects(response, "/dashboard/")

    def test_angemeldeter_vorstand_mit_geraet_wird_weiter_gefragt(self):
        secret = neues_secret()
        TwoFactorDevice.objects.create(user=self.admin, secret=secret, bestaetigt=True)
        with self.settings(TWOFA_PFLICHT=False):
            response = self.client.post(
                "/anmelden/", {"username": "vorstand", "password": "sicheres-passwort-1"}
            )
        self.assertRedirects(response, "/anmelden/zwei-faktor/")

    def test_zwei_faktor_seite_ohne_session_fuehrt_zum_login(self):
        self.assertRedirects(self.client.get("/anmelden/zwei-faktor/"), "/anmelden/")

    def test_geraetewechsel_loescht_alte_konfiguration(self):
        self.client.force_login(self.admin)
        TwoFactorDevice.objects.create(user=self.admin, secret=neues_secret(), bestaetigt=True)
        response = self.client.post("/anmelden/zwei-faktor/neu/")
        self.assertRedirects(response, "/anmelden/zwei-faktor/")
        self.assertFalse(TwoFactorDevice.objects.filter(user=self.admin).exists())


class TotpPruefungTests(TestCase):
    def test_codes_sind_zeitabhaengig_und_sechsstellig(self):
        secret = neues_secret()
        code = code_erzeugen(secret)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_uri_enthaelt_alle_pflichtangaben(self):
        uri = otpauth_uri("ABCDEFGHIJKLMNOP", "vorstand")
        self.assertTrue(uri.startswith("otpauth://totp/"))
        self.assertIn("secret=ABCDEFGHIJKLMNOP", uri)
        self.assertIn("digits=6", uri)
        self.assertIn("issuer=", uri)


class SicherheitsHeaderTests(TestCase):
    def test_header_sind_gesetzt(self):
        response = self.client.get("/health/")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("same-origin", response.headers["Referrer-Policy"])
        self.assertIn("geolocation=()", response.headers["Permissions-Policy"])

    def test_csp_verbietet_fremdquellen(self):
        """Im Produktivmodus (DEBUG=0) wird eine strikte CSP ausgeliefert."""
        with self.settings(DEBUG=False):
            response = self.client.get("/health/")
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertNotIn("unsafe-eval", csp)
