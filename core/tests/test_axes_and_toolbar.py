"""Tests für Brute-Force-Schutz (django-axes) und Dev-Profiling (django-debug-toolbar).

Gemäß PRD N1.6 (Härtung), N2.2 (Performance) und ADR-015.
"""

from axes.models import AccessAttempt
from axes.utils import reset
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings


@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=5, AXES_RESET_ON_SUCCESS=True)
class AxesBruteForceTests(TestCase):
    """Prüft den Brute-Force-Schutz bei wiederholt fehlerhaften Anmeldeversuchen."""

    def setUp(self):
        reset()
        self.user = User.objects.create_user(
            username="schachspieler",
            password="sicheres-passwort-1",
        )

    def tearDown(self):
        reset()

    def test_erfolgreiche_anmeldung_funktioniert(self):
        """Reguläre Anmeldung mit korrektem Passwort gelingt."""
        response = self.client.post(
            "/anmelden/",
            {"username": "schachspieler", "password": "sicheres-passwort-1"},
        )
        self.assertRedirects(response, "/dashboard/")
        self.assertEqual(AccessAttempt.objects.count(), 0)

    def test_fehlversuche_bis_zum_limit_erlaubt(self):
        """Bis zu 4 Fehlversuche führen zu Fehlermeldung, sperren aber noch nicht."""
        for _ in range(4):
            response = self.client.post(
                "/anmelden/",
                {"username": "schachspieler", "password": "falsches-passwort"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Benutzername oder Passwort ist nicht korrekt")

        self.assertEqual(AccessAttempt.objects.count(), 1)
        self.assertEqual(AccessAttempt.objects.first().failures_since_start, 4)

    def test_fuenfter_fehlversuch_sperrt_zugang_negativtest(self):
        """Negativtest: Nach 5 Fehlversuchen wird der Zugang gesperrt (HTTP 429 + Lockout-Seite)."""
        # 5 Fehlversuche hintereinander
        for _ in range(5):
            self.client.post(
                "/anmelden/",
                {"username": "schachspieler", "password": "falsches-passwort"},
            )

        # 6. Versuch (auch mit richtigem Passwort) wird mit 429 (Too Many Requests) abgewiesen
        gesperrt_response = self.client.post(
            "/anmelden/",
            {"username": "schachspieler", "password": "sicheres-passwort-1"},
        )
        self.assertEqual(gesperrt_response.status_code, 429)
        self.assertTemplateUsed(gesperrt_response, "core/lockout.html")
        self.assertContains(gesperrt_response, "Zugang gesperrt", status_code=429)
        self.assertContains(gesperrt_response, "Zu viele fehlgeschlagene Anmeldeversuche", status_code=429)

    def test_erfolgreicher_login_setzt_zaehler_zurueck(self):
        """Ein erfolgreicher Login vor Erreichen des Limits setzt den Fehlversuchszähler zurück."""
        # 2 Fehlversuche
        for _ in range(2):
            self.client.post(
                "/anmelden/",
                {"username": "schachspieler", "password": "falsches-passwort"},
            )
        self.assertEqual(AccessAttempt.objects.count(), 1)

        # Erfolgreicher Login
        response = self.client.post(
            "/anmelden/",
            {"username": "schachspieler", "password": "sicheres-passwort-1"},
        )
        self.assertRedirects(response, "/dashboard/")
        # Zähler muss gelöscht sein
        self.assertEqual(AccessAttempt.objects.count(), 0)


class DebugToolbarTests(TestCase):
    """Prüft die Verfügbarkeit bzw. Nichterreichbarkeit der django-debug-toolbar."""

    @override_settings(DEBUG=False)
    def test_debug_toolbar_nicht_erreichbar_in_produktion_negativtest(self):
        """Negativtest: Bei DEBUG=False liefert die Debug-Toolbar-Route 404."""
        response = self.client.get("/__debug__/")
        self.assertEqual(response.status_code, 404)

    def test_debug_toolbar_callback_pruefung(self):
        """Der Callback show_debug_toolbar respektiert DEBUG und schließt AJAX aus."""
        from django.test import RequestFactory

        from config.settings import show_debug_toolbar

        factory = RequestFactory()

        with override_settings(DEBUG=True):
            req_normal = factory.get("/dashboard/")
            self.assertTrue(show_debug_toolbar(req_normal))

            req_ajax = factory.get("/dashboard/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
            self.assertFalse(show_debug_toolbar(req_ajax))

        with override_settings(DEBUG=False):
            req_prod = factory.get("/dashboard/")
            self.assertFalse(show_debug_toolbar(req_prod))


class DjangoExtensionsTests(TestCase):
    """Prüft die Einbindung von django_extensions für Entwicklungs-Werkzeuge."""

    def test_extensions_management_commands_verfuegbar(self):
        """Management-Befehle von django_extensions (z. B. validate_templates) sind registriert."""
        from django.core.management import get_commands

        commands = get_commands()
        self.assertIn("validate_templates", commands)
        self.assertIn("show_urls", commands)
        self.assertIn("shell_plus", commands)

    def test_extensions_nicht_in_produktion_negativtest(self):
        """Negativtest: In config/production.py ist DEBUG=False und extensions wird nicht geladen."""
        import os

        from django.core.exceptions import ImproperlyConfigured

        # config/production erfordert SECRET_KEY und IBAN_FERNET_KEY
        env_backup = dict(os.environ)
        try:
            os.environ["DJANGO_SECRET_KEY"] = "prod-test-key-12345"
            os.environ["IBAN_FERNET_KEY"] = "up3_XszoFQiTs6TmInARNOIqBlEeh7V_7e46vfQ_g-E="
            os.environ["EMAIL_BACKEND"] = "django.core.mail.backends.smtp.EmailBackend"

            import importlib

            import config.production as prod_conf

            importlib.reload(prod_conf)
            self.assertFalse(prod_conf.DEBUG)
        except ImproperlyConfigured:
            pass
        finally:
            os.environ.clear()
            os.environ.update(env_backup)


class ReverseProxyAndIpTests(TestCase):
    """Prüft die korrekte IP-Ermittlung hinter Reverse-Proxies und Axes-Proxy-Konfiguration (SEC-06)."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_axes_proxy_einstellungen(self):
        """Prüft, dass Axes für den Betrieb hinter einem Reverse-Proxy vorkonfiguriert ist."""
        from django.conf import settings

        self.assertEqual(settings.AXES_PROXY_COUNT, 1)
        self.assertEqual(settings.AXES_META_PRE_NAME, "HTTP_X_FORWARDED_FOR")

    def test_ip_extraktion_mit_x_forwarded_for(self):
        """_ip extrahiert die echte Client-IP aus X-Forwarded-For auch bei Proxy-Ketten."""
        from core.signals import _ip

        request = self.factory.get("/dashboard/", HTTP_X_FORWARDED_FOR="203.0.113.195, 10.0.0.1")
        self.assertEqual(_ip(request), "203.0.113.195")

    def test_ip_extraktion_fallback_remote_addr(self):
        """_ip fällt auf REMOTE_ADDR zurück, falls kein X-Forwarded-For Header vorliegt."""
        from core.signals import _ip

        request = self.factory.get("/dashboard/", REMOTE_ADDR="198.51.100.4")
        self.assertEqual(_ip(request), "198.51.100.4")

    def test_ip_extraktion_ohne_request_negativtest(self):
        """Negativtest: Bei None als Request wird ein sicherer Ersatzwert geliefert."""
        from core.signals import _ip

        self.assertEqual(_ip(None), "—")

    def test_anmeldeversuch_protokolliert_client_ip_aus_reverse_proxy(self):
        """Fehlgeschlagener und erfolgreicher Login protokollieren die Client-IP aus X-Forwarded-For."""
        from core.models import AuditLog

        User.objects.create_user(username="proxy_spieler", password="sicheres-passwort-1")

        # Fehlversuch mit X-Forwarded-For
        self.client.post(
            "/anmelden/",
            {"username": "proxy_spieler", "password": "falsches-passwort"},
            HTTP_X_FORWARDED_FOR="203.0.113.50, 10.0.0.1",
        )
        fehl_log = AuditLog.objects.filter(aktion="Anmeldung abgelehnt").latest("zeitpunkt")
        self.assertIn("IP: 203.0.113.50", fehl_log.text)

        # Erfolgreicher Login mit X-Forwarded-For
        self.client.post(
            "/anmelden/",
            {"username": "proxy_spieler", "password": "sicheres-passwort-1"},
            HTTP_X_FORWARDED_FOR="203.0.113.50, 10.0.0.1",
        )
        erfolg_log = AuditLog.objects.filter(aktion="Anmeldung").latest("zeitpunkt")
        self.assertIn("IP: 203.0.113.50", erfolg_log.text)

