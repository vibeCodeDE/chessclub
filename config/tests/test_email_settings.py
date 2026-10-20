import importlib
import os
import sys
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

EMAIL_ENV = {
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "EMAIL_HOST": "smtp.verein.example",
    "EMAIL_PORT": "465",
    "EMAIL_HOST_USER": "verein",
    "EMAIL_HOST_PASSWORD": "geheim",
    "EMAIL_USE_TLS": "0",
    "DEFAULT_FROM_EMAIL": "vorstand@verein.example",
}


def load_settings(**overrides):
    """config.settings neu laden – mit den übergebenen Env-Werten."""
    env = {**EMAIL_ENV, **overrides}
    with patch.dict(os.environ, env):
        importlib.import_module("config.settings")
        return importlib.reload(sys.modules["config.settings"])


class EmailSettingsTests(SimpleTestCase):
    """SMTP des Vereins muss komplett per Env konfigurierbar sein (PRD §2)."""

    def tearDown(self):
        # Reload außerhalb von patch.dict – mit ursprünglicher Umgebung,
        # damit Folgetests den Dev-Default sehen.
        importlib.reload(sys.modules["config.settings"])

    def test_smtp_werte_kommen_aus_der_umgebung(self):
        settings = load_settings()

        self.assertEqual(
            settings.EMAIL_BACKEND,
            "django.core.mail.backends.smtp.EmailBackend",
        )
        self.assertEqual(settings.EMAIL_HOST, "smtp.verein.example")
        self.assertEqual(settings.EMAIL_PORT, 465)
        self.assertEqual(settings.EMAIL_HOST_USER, "verein")
        self.assertEqual(settings.EMAIL_HOST_PASSWORD, "geheim")
        self.assertFalse(settings.EMAIL_USE_TLS)
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, "vorstand@verein.example")

    def test_server_email_folgt_dem_absender(self):
        settings = load_settings()

        self.assertEqual(settings.SERVER_EMAIL, "vorstand@verein.example")

    def test_ohne_env_herrschen_dev_defaults(self):
        with patch.dict(os.environ, {"DJANGO_DEBUG": "1"}, clear=True):
            settings = importlib.reload(sys.modules["config.settings"])

        self.assertEqual(
            settings.EMAIL_BACKEND,
            "django.core.mail.backends.console.EmailBackend",
        )
        self.assertEqual(settings.EMAIL_HOST, "localhost")
        self.assertEqual(settings.EMAIL_PORT, 587)
        self.assertTrue(settings.EMAIL_USE_TLS)

    def test_production_uebernimmt_die_smtp_konfiguration(self):
        # production.py liest Pflicht-Variablen beim Import aus der Umgebung,
        # daher Settings- und Production-Reload innerhalb desselben patch.dict.
        env = {**EMAIL_ENV, "DJANGO_SECRET_KEY": "test-key", "IBAN_FERNET_KEY": "x"}
        with patch.dict(os.environ, env):
            load_settings()
            production = importlib.reload(
                importlib.import_module("config.production")
            )

        self.assertEqual(production.EMAIL_HOST, "smtp.verein.example")
        self.assertFalse(production.DEBUG)
        self.assertTrue(production.SESSION_COOKIE_SECURE)


def load_production(**overrides):
    """config.production neu laden – mit gesetzten Pflicht-Variablen."""
    env = {
        **EMAIL_ENV,
        "DJANGO_SECRET_KEY": "test-key",
        "IBAN_FERNET_KEY": "test-fernet-key",
        **overrides,
    }
    with patch.dict(os.environ, env):
        importlib.import_module("config.settings")
        importlib.reload(sys.modules["config.settings"])
        return importlib.reload(importlib.import_module("config.production"))


class ProductionHardeningTests(SimpleTestCase):
    """Härtung aus .env.prod.example muss in production.py tatsächlich greifen."""

    def tearDown(self):
        # Reload unter vollständiger Env – config.production wirft ohne
        # DJANGO_SECRET_KEY/IBAN_FERNET_KEY beim Import (so soll es sein).
        env = {
            **EMAIL_ENV,
            "DJANGO_SECRET_KEY": "test-key",
            "IBAN_FERNET_KEY": "test-fernet-key",
        }
        with patch.dict(os.environ, env):
            importlib.reload(sys.modules["config.settings"])
            importlib.reload(importlib.import_module("config.production"))

    def test_https_und_hsts_sind_standardmaessig_aktiv(self):
        production = load_production()

        self.assertTrue(production.SECURE_SSL_REDIRECT)
        self.assertEqual(production.SECURE_HSTS_SECONDS, 31536000)

    def test_hsts_laeisst_sich_abschalten(self):
        # Negativtest: eine Env ohne die Variablen darf die Härtung nicht
        # "raten" – hier wird sie ausdrücklich abgeschaltet.
        production = load_production(SECURE_SSL_REDIRECT="0", SECURE_HSTS_SECONDS="0")

        self.assertFalse(production.SECURE_SSL_REDIRECT)
        self.assertEqual(production.SECURE_HSTS_SECONDS, 0)

    def test_ohne_iban_schlüssel_startet_die_produktion_nicht(self):
        # Negativtest: ADR-010 verlangt den Schlüssel; ohne ihn darf der
        # Import nicht stillschweigend durchgehen.
        env = {**EMAIL_ENV, "DJANGO_SECRET_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            importlib.import_module("config.settings")
            importlib.reload(sys.modules["config.settings"])
            with self.assertRaises(ImproperlyConfigured):
                importlib.reload(importlib.import_module("config.production"))
