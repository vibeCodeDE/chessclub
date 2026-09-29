"""Vercel-Betrieb: Hosts, Datenbank-URL und Cookies.

Regression: Die Vercel-Domain lieferte „Bad Request (400)“, weil ``ALLOWED_HOSTS``
nur ``localhost`` kannte (Django: ``DisallowedHost``).
"""

import importlib.util
import inspect
import os
import re
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ConnectionHandler
from django.http.request import validate_host
from django.test import Client, SimpleTestCase, TestCase

SETTINGS_DATEI = Path(__file__).resolve().parents[1] / "settings.py"

# Umgebungswerte, die config.settings auswertet – für reproduzierbare Tests entfernt.
GELESEN = (
    "VERCEL",
    "VERCEL_ENV",
    "VERCEL_URL",
    "VERCEL_BRANCH_URL",
    "VERCEL_PROJECT_PRODUCTION_URL",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_DEBUG",
    "DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRES_HOST",
    "POSTGRES_DB",
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
)

VERCEL = {
    "VERCEL": "1",
    "VERCEL_ENV": "production",
    "VERCEL_URL": "chessclub-7f3k2-vibecode.vercel.app",
    "VERCEL_BRANCH_URL": "chessclub-git-master-vibecode.vercel.app",
    "VERCEL_PROJECT_PRODUCTION_URL": "chessclub-iota.vercel.app",
}

NEON_URL = (
    "postgresql://neondb_owner:p%40ss%3Aw%2Frd%231"
    "@ep-cool-123456-pooler.eu-central-1.aws.neon.tech/neondb"
    "?sslmode=require&channel_binding=require"
)


def lade_settings(**env):
    """``config/settings.py`` frisch in ein eigenes Modul laden.

    Nur mit den übergebenen Umgebungswerten; ``config.settings`` selbst (und damit
    alles, was es per ``import *`` übernimmt) bleibt unberührt.
    """
    umgebung = {k: v for k, v in os.environ.items() if k not in GELESEN}
    umgebung.update(env)
    spec = importlib.util.spec_from_file_location("config._settings_unter_test", SETTINGS_DATEI)
    modul = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, umgebung, clear=True):
        spec.loader.exec_module(modul)
    return modul


class VercelHostsTests(SimpleTestCase):
    def test_ohne_vercel_bleiben_nur_lokale_hosts(self):
        settings = lade_settings()
        self.assertFalse(settings.ON_VERCEL)
        self.assertEqual(settings.ALLOWED_HOSTS, ["localhost", "127.0.0.1"])

    def test_vercel_domains_sind_erlaubt(self):
        settings = lade_settings(**VERCEL)
        self.assertTrue(settings.ON_VERCEL)
        for host in (
            "chessclub-iota.vercel.app",  # Produktions-Alias
            VERCEL["VERCEL_URL"],  # Deployment-URL
            VERCEL["VERCEL_BRANCH_URL"],  # Branch-Alias
            "chessclub-vibecode.vercel.app",  # weitere Alias-Domain des Projekts
            "localhost",
        ):
            with self.subTest(host=host):
                self.assertTrue(validate_host(host, settings.ALLOWED_HOSTS))

    def test_fremde_hosts_bleiben_gesperrt(self):
        settings = lade_settings(**VERCEL)
        for host in ("evil.example.com", "vercel.app.evil.example.com", "evil-vercel.app"):
            with self.subTest(host=host):
                self.assertFalse(validate_host(host, settings.ALLOWED_HOSTS))

    def test_eigene_produktionsdomain_wird_erlaubt(self):
        settings = lade_settings(**{**VERCEL, "VERCEL_PROJECT_PRODUCTION_URL": "verein.example.de"})
        self.assertTrue(validate_host("verein.example.de", settings.ALLOWED_HOSTS))

    def test_vercel_urls_werden_von_schema_und_slash_befreit(self):
        settings = lade_settings(
            VERCEL="1", VERCEL_PROJECT_PRODUCTION_URL="https://verein.example.de/"
        )
        self.assertIn("verein.example.de", settings.ALLOWED_HOSTS)

    def test_explizite_hosts_bleiben_erhalten(self):
        settings = lade_settings(**VERCEL, DJANGO_ALLOWED_HOSTS="portal.example.de, localhost")
        self.assertIn("portal.example.de", settings.ALLOWED_HOSTS)
        self.assertEqual(settings.ALLOWED_HOSTS.count("localhost"), 1)
        self.assertTrue(validate_host("chessclub-iota.vercel.app", settings.ALLOWED_HOSTS))


class VercelAnfrageTests(TestCase):
    """Die Anfrage läuft durch den echten Middleware-Stack (wie im Deployment)."""

    host = "chessclub-iota.vercel.app"

    def test_vercel_domain_liefert_nicht_mehr_400(self):
        hosts = lade_settings(**VERCEL).ALLOWED_HOSTS
        with self.settings(ALLOWED_HOSTS=hosts):
            response = self.client.get("/health/", HTTP_HOST=self.host, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_ohne_vercel_konfiguration_bleibt_es_bei_400(self):
        """Belegt, dass der Test den ursprünglichen Fehler tatsächlich abbildet."""
        hosts = lade_settings().ALLOWED_HOSTS
        with self.settings(ALLOWED_HOSTS=hosts):
            response = self.client.get("/health/", HTTP_HOST=self.host, secure=True)
        self.assertEqual(response.status_code, 400)

    def _login_post(self, settings_modul):
        """Login-POST mit CSRF-Prüfung; die Runtime meldet nur ``http`` (Proxy-Header gesetzt)."""
        ueberschreibungen = {"ALLOWED_HOSTS": settings_modul.ALLOWED_HOSTS}
        proxy = getattr(settings_modul, "SECURE_PROXY_SSL_HEADER", None)
        if proxy:
            ueberschreibungen["SECURE_PROXY_SSL_HEADER"] = proxy
        kopf = {"HTTP_HOST": self.host, "HTTP_X_FORWARDED_PROTO": "https"}
        client = Client(enforce_csrf_checks=True)
        with self.settings(**ueberschreibungen):
            seite = client.get("/anmelden/", **kopf)
            token = re.search(
                r'name="csrfmiddlewaretoken" value="([^"]+)"', seite.content.decode()
            ).group(1)
            return client.post(
                "/anmelden/",
                {"username": "niemand", "password": "falsch", "csrfmiddlewaretoken": token},
                HTTP_ORIGIN=f"https://{self.host}",
                **kopf,
            )

    def test_login_post_besteht_die_csrf_origin_pruefung(self):
        response = self._login_post(lade_settings(**VERCEL))
        self.assertEqual(response.status_code, 200)  # Formular mit Fehlermeldung, kein 403

    def test_ohne_proxy_header_scheitert_die_origin_pruefung(self):
        """Begründet ``SECURE_PROXY_SSL_HEADER``: sonst hielte Django die Anfrage für ``http``."""
        ohne = lade_settings(**VERCEL)
        del ohne.SECURE_PROXY_SSL_HEADER
        self.assertEqual(self._login_post(ohne).status_code, 403)


class VercelCookieTests(SimpleTestCase):
    def test_vercel_nutzt_standardmaessig_sichere_cookies(self):
        settings = lade_settings(**VERCEL)
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https"))

    def test_lokal_bleibt_http_entwicklung_moeglich(self):
        settings = lade_settings()
        self.assertFalse(settings.SESSION_COOKIE_SECURE)
        self.assertFalse(settings.CSRF_COOKIE_SECURE)
        self.assertFalse(hasattr(settings, "SECURE_PROXY_SSL_HEADER"))

    def test_umgebung_kann_die_vercel_vorgabe_uebersteuern(self):
        settings = lade_settings(**VERCEL, SESSION_COOKIE_SECURE="0", CSRF_COOKIE_SECURE="0")
        self.assertFalse(settings.SESSION_COOKIE_SECURE)
        self.assertFalse(settings.CSRF_COOKIE_SECURE)


class DatenbankUrlTests(SimpleTestCase):
    def test_ohne_angaben_bleibt_sqlite(self):
        self.assertEqual(
            lade_settings().DATABASES["default"]["ENGINE"], "django.db.backends.sqlite3"
        )

    def test_neon_url_wird_zur_postgres_konfiguration(self):
        db = lade_settings(DATABASE_URL=NEON_URL).DATABASES["default"]
        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(db["NAME"], "neondb")
        self.assertEqual(db["USER"], "neondb_owner")
        self.assertEqual(db["PASSWORD"], "p@ss:w/rd#1")  # in der URL prozentkodiert
        self.assertEqual(db["HOST"], "ep-cool-123456-pooler.eu-central-1.aws.neon.tech")
        self.assertEqual(db["PORT"], "")
        self.assertEqual(db["OPTIONS"]["sslmode"], "require")
        self.assertEqual(db["OPTIONS"]["channel_binding"], "require")

    def test_konfiguration_ist_pooler_tauglich(self):
        db = lade_settings(DATABASE_URL=NEON_URL).DATABASES["default"]
        self.assertTrue(db["DISABLE_SERVER_SIDE_CURSORS"])
        self.assertIsNone(db["OPTIONS"]["prepare_threshold"])

    def test_fremde_url_parameter_werden_verworfen(self):
        """Supabase hängt ``supa=…`` an – libpq würde daran scheitern."""
        url = "postgres://u:p@aws-0.pooler.supabase.com:6543/postgres?sslmode=require&supa=base-pooler.x"
        db = lade_settings(POSTGRES_URL=url).DATABASES["default"]
        self.assertEqual(db["PORT"], "6543")
        self.assertEqual(db["OPTIONS"]["sslmode"], "require")
        self.assertNotIn("supa", db["OPTIONS"])

    def test_database_url_hat_vorrang(self):
        settings = lade_settings(
            DATABASE_URL=NEON_URL, POSTGRES_URL="postgres://x:y@z/anders", POSTGRES_HOST="db"
        )
        self.assertEqual(settings.DATABASES["default"]["NAME"], "neondb")

    def test_einzelwerte_ohne_url_bleiben_unveraendert(self):
        """docker-compose: POSTGRES_HOST und Co. funktionieren wie bisher."""
        db = lade_settings(POSTGRES_HOST="db", POSTGRES_DB="schachverein").DATABASES["default"]
        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual((db["HOST"], db["NAME"]), ("db", "schachverein"))
        self.assertNotIn("OPTIONS", db)

    def test_keine_postgres_url_wird_abgelehnt(self):
        with self.assertRaises(ImproperlyConfigured):
            lade_settings(DATABASE_URL="mysql://u:p@h/db")

    @skipUnless(importlib.util.find_spec("psycopg"), "psycopg nicht installiert")
    def test_django_backend_und_psycopg_nehmen_die_optionen_an(self):
        import psycopg

        db = lade_settings(DATABASE_URL=NEON_URL).DATABASES["default"]
        params = ConnectionHandler({"default": db})["default"].get_connection_params()
        self.assertEqual(params["dbname"], "neondb")
        self.assertEqual(params["password"], "p@ss:w/rd#1")
        self.assertEqual(params["sslmode"], "require")
        # prepare_threshold ist ein psycopg-Argument, kein libpq-Parameter
        self.assertIn("prepare_threshold", inspect.signature(psycopg.Connection.connect).parameters)
        self.assertIsNone(params["prepare_threshold"])
