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

    def test_negativ_fuenf_fehlversuche_sperren_den_zwei_faktor_zugang(self):
        secret = neues_secret()
        TwoFactorDevice.objects.create(user=self.admin, secret=secret, bestaetigt=True)
        self.client.post("/anmelden/", {"username": "vorstand", "password": "sicheres-passwort-1"})

        # 4 Fehlversuche: bleibt auf zwei_faktor und zeigt Restversuche
        for i in range(1, 5):
            res = self.client.post("/anmelden/zwei-faktor/", {"code": f"00000{i}"})
            self.assertEqual(res.status_code, 200)
            self.assertContains(res, f"noch {5 - i} Versuch")

        # 5. Fehlversuch: Sperrung und Redirect zu /anmelden/
        res5 = self.client.post("/anmelden/zwei-faktor/", {"code": "000005"})
        self.assertRedirects(res5, "/anmelden/")
        self.assertNotIn("_2fa_user_id", self.client.session)

        # Neuer Aufruf von /anmelden/zwei-faktor/ leitet nun direkt zu /anmelden/ um (Session bereinigt)
        res_neu = self.client.get("/anmelden/zwei-faktor/")
        self.assertRedirects(res_neu, "/anmelden/")

    def test_negativ_replay_schutz_verhindert_wiederverwendung_desselben_codes(self):
        secret = neues_secret()
        TwoFactorDevice.objects.create(user=self.admin, secret=secret, bestaetigt=True)
        code = code_erzeugen(secret)

        # Erste Anmeldung mit Code erfolgreich
        self.client.post("/anmelden/", {"username": "vorstand", "password": "sicheres-passwort-1"})
        res1 = self.client.post("/anmelden/zwei-faktor/", {"code": code})
        self.assertRedirects(res1, "/dashboard/")
        self.client.logout()

        # Zweite Anmeldung mit demselben Code im selben Zeitfenster schlägt fehl
        self.client.post("/anmelden/", {"username": "vorstand", "password": "sicheres-passwort-1"})
        res2 = self.client.post("/anmelden/zwei-faktor/", {"code": code})
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, "Der Code stimmt nicht")
        self.assertNotIn("_auth_user_id", self.client.session)


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


class FehlerseitenTests(TestCase):
    def test_404_seite_rendert_passend(self):
        response = self.client.get("/eine-seite-die-es-nicht-gibt/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Dieser Zug ging", status_code=404)

    def test_403_seite_rendert_passend(self):
        from django.core.exceptions import PermissionDenied
        from django.test import RequestFactory
        from django.views.defaults import permission_denied

        request = RequestFactory().get("/geheim/")
        response = permission_denied(request, PermissionDenied("Keine Berechtigung"))
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Zugriff", response.content)
        self.assertIn(b"nicht gestattet", response.content)

    def test_500_seite_rendert_ohne_kontextfehler(self):
        from django.test import RequestFactory
        from django.views.defaults import server_error

        request = RequestFactory().get("/fehler/")
        response = server_error(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Serverfehler", response.content)
        self.assertIn(b"Technischer", response.content)

