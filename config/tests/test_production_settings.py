import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

GOOD_ENV = {
    "DJANGO_SECRET_KEY": "prod-test-key",
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
}

WURZEL = Path(__file__).resolve().parents[2]


def load_production(**overrides):
    """config.production (neu) laden – nur mit den übergebenen Env-Werten."""
    env = {**GOOD_ENV, **overrides}
    with patch.dict(os.environ, env):
        importlib.import_module("config.production")
        return importlib.reload(sys.modules["config.production"])


class ProductionSettingsTests(SimpleTestCase):
    def tearDown(self):
        load_production()

    def test_secret_key_must_be_set(self):
        for value in ("", "dev-insecure-key"):
            with self.subTest(secret=value):
                with self.assertRaises(ImproperlyConfigured):
                    load_production(DJANGO_SECRET_KEY=value)

    def test_email_backend_must_not_be_console(self):
        for value in ("", "django.core.mail.backends.console.EmailBackend"):
            with self.subTest(backend=value):
                with self.assertRaises(ImproperlyConfigured):
                    load_production(EMAIL_BACKEND=value)

    def test_email_backend_ist_die_vorlagenvariable(self):
        """Die Vorlage und die Settings sprechen dieselbe Variable an."""
        vorlage = (WURZEL / ".env.prod.example").read_text(encoding="utf-8")
        self.assertIn("EMAIL_BACKEND=django.core.mail", vorlage)
        production = load_production()
        self.assertEqual(production.EMAIL_BACKEND, GOOD_ENV["EMAIL_BACKEND"])

    def test_prod_compose_aktiviert_die_produktions_settings(self):
        """Ohne DJANGO_SETTINGS_MODULE liefe der Dev-Fallback mit."""
        compose = (WURZEL / "docker-compose.prod.yml").read_text(encoding="utf-8")
        self.assertIn('DJANGO_SETTINGS_MODULE: "config.production"', compose)

    def test_debug_is_off_even_if_env_requests_it(self):
        production = load_production(DJANGO_DEBUG="1")
        self.assertFalse(production.DEBUG)

    def test_session_and_csrf_cookies_are_secure(self):
        production = load_production()
        self.assertTrue(production.SESSION_COOKIE_SECURE)
        self.assertTrue(production.CSRF_COOKIE_SECURE)

    def test_secret_key_comes_from_environment(self):
        production = load_production(DJANGO_SECRET_KEY="aus-env")
        self.assertEqual(production.SECRET_KEY, "aus-env")

    def test_ratelimit_ip_meta_key_defaults_to_extractor(self):
        production = load_production()
        self.assertEqual(production.RATELIMIT_IP_META_KEY, "core.middleware.get_ratelimit_ip")

    def test_ratelimit_ip_meta_key_can_be_overridden(self):
        production = load_production(RATELIMIT_IP_META_KEY="HTTP_X_REAL_IP")
        self.assertEqual(production.RATELIMIT_IP_META_KEY, "HTTP_X_REAL_IP")


def load_base_settings(**overrides):
    """config.settings (neu) laden – nur mit den übergebenen Env-Werten."""
    with patch.dict(os.environ, overrides, clear=True):
        importlib.import_module("config.settings")
        return importlib.reload(sys.modules["config.settings"])


class BaseSettingsSecurityTests(SimpleTestCase):
    """Sicherheits-Gegenprobe: config.settings darf im Nicht-Debug-Modus (DEBUG=False)
    niemals mit Default- oder leerem Secret-Key starten."""

    def tearDown(self):
        with patch.dict(os.environ, {"DJANGO_DEBUG": "1", "DJANGO_SECRET_KEY": "dev-only-secret-key"}):
            importlib.reload(sys.modules["config.settings"])

    def test_settings_secret_key_required_when_debug_false(self):
        """Negativtest: Bei DEBUG=False führt ein fehlender oder Standard-Schlüssel zum Abbruch."""
        for val in ("", "dev-insecure-key"):
            with self.subTest(secret=val):
                with self.assertRaises(ImproperlyConfigured):
                    load_base_settings(DJANGO_DEBUG="0", DJANGO_SECRET_KEY=val)

    def test_settings_secret_key_required_when_debug_not_set(self):
        """Negativtest: Ohne DJANGO_DEBUG (Default ist DEBUG=False) wird der Dev-Key verweigert."""
        with self.assertRaises(ImproperlyConfigured):
            load_base_settings(DJANGO_SECRET_KEY="dev-insecure-key")

    def test_settings_secret_key_accepted_when_valid(self):
        """Positivtest: Ein gültiger Secret Key wird auch bei DEBUG=False übernommen."""
        settings = load_base_settings(DJANGO_DEBUG="0", DJANGO_SECRET_KEY="sicherer-schluessel-fuer-prod")
        self.assertEqual(settings.SECRET_KEY, "sicherer-schluessel-fuer-prod")

    def test_settings_dev_fallback_allowed_when_debug_true(self):
        """Positivtest Dev: Bei DEBUG=True ist der Dev-Fallback-Schlüssel weiterhin erlaubt."""
        settings = load_base_settings(DJANGO_DEBUG="1")
        self.assertEqual(settings.SECRET_KEY, "dev-insecure-key")
