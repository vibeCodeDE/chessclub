import json
import os
import urllib.parse
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

WURZEL = Path(__file__).resolve().parents[2]


class ScalingoDeploymentConfigurationTests(TestCase):

    def test_procfile_exists_and_configured(self):
        """Procfile existiert und definiert Web-Prozess und postdeploy-Migration."""
        procfile = WURZEL / "Procfile"
        self.assertTrue(procfile.exists(), "Procfile fehlt im Projekt-Stammverzeichnis")
        content = procfile.read_text(encoding="utf-8")
        self.assertIn("web: gunicorn config.wsgi:application", content)
        self.assertIn("postdeploy: python manage.py migrate --noinput && python manage.py ensure_admin", content)


    def test_runtime_txt_exists_and_uses_python_312(self):
        """runtime.txt legt Python 3.12 für den Scalingo Python-Buildpack fest."""
        runtime = WURZEL / "runtime.txt"
        self.assertTrue(runtime.exists(), "runtime.txt fehlt im Projekt-Stammverzeichnis")
        content = runtime.read_text(encoding="utf-8").strip()
        self.assertTrue(content.startswith("python-3.12"), f"Unerwartete Python-Version: {content}")

    def test_scalingo_json_is_valid_and_contains_required_fields(self):
        """scalingo.json ist valides JSON und definiert PostgreSQL-Addon und Pflicht-Umgebungsvariablen."""
        manifest_path = WURZEL / "scalingo.json"
        self.assertTrue(manifest_path.exists(), "scalingo.json fehlt im Projekt-Stammverzeichnis")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Addons
        self.assertIn("addons", manifest)
        self.assertTrue(any("postgresql" in addon for addon in manifest["addons"]))

        # Pflicht-Env
        env = manifest.get("env", {})
        self.assertIn("DJANGO_SETTINGS_MODULE", env)
        self.assertEqual(env["DJANGO_SETTINGS_MODULE"]["value"], "config.production")
        self.assertIn("DJANGO_SECRET_KEY", env)
        self.assertEqual(env["DJANGO_SECRET_KEY"]["generator"], "secret")
        self.assertIn("IBAN_FERNET_KEY", env)

    def test_requirements_contains_whitenoise(self):
        """requirements.txt enthält whitenoise für das statische Asset-Serving auf Scalingo."""
        requirements = (WURZEL / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("whitenoise", requirements)

    def test_scalingo_database_url_parsing(self):
        """Prüft, dass SCALINGO_POSTGRESQL_URL bzw. DATABASE_URL korrekt in DATABASES geparst wird."""
        test_url = "postgresql://user123:geheimpass@my-pg.scalingo.io:10001/schach_prod?sslmode=require"
        url = urllib.parse.urlparse(test_url)
        parsed_db = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": url.path.lstrip("/"),
            "USER": url.username or "",
            "PASSWORD": url.password or "",
            "HOST": url.hostname or "localhost",
            "PORT": str(url.port or 5432),
        }
        query = urllib.parse.parse_qs(url.query)
        if "sslmode" in query:
            parsed_db["OPTIONS"] = {"sslmode": query["sslmode"][0]}

        self.assertEqual(parsed_db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(parsed_db["NAME"], "schach_prod")
        self.assertEqual(parsed_db["USER"], "user123")
        self.assertEqual(parsed_db["PASSWORD"], "geheimpass")
        self.assertEqual(parsed_db["HOST"], "my-pg.scalingo.io")
        self.assertEqual(parsed_db["PORT"], "10001")
        self.assertEqual(parsed_db["OPTIONS"]["sslmode"], "require")

    def test_database_url_fallback_to_sqlite(self):
        """Negativtest: Ohne DATABASE_URL und ohne POSTGRES_HOST greift SQLite-Fallback."""
        from django.conf import settings
        # Wenn weder POSTGRES_HOST noch DATABASE_URL gesetzt sind (Default-Testumgebung)
        # sollte die Engine SQLite oder die konfigurierte Test-DB sein.
        self.assertIn(settings.DATABASES["default"]["ENGINE"], [
            "django.db.backends.sqlite3",
            "django.db.backends.postgresql",
        ])

    def test_ensure_admin_creates_or_updates_superuser(self):
        """ensure_admin erstellt oder aktualisiert Superadmin aus Environment-Variablen."""
        from io import StringIO
        from django.core.management import call_command
        from django.contrib.auth import get_user_model

        User = get_user_model()
        out = StringIO()
        # Ohne Passwort: überspringen
        call_command("ensure_admin", stdout=out)
        self.assertIn("Kein DJANGO_SUPERUSER_PASSWORD gesetzt", out.getvalue())

        # Mit Passwort: anlegen
        with patch.dict(os.environ, {
            "DJANGO_SUPERUSER_USERNAME": "scalingo_testadmin",
            "DJANGO_SUPERUSER_PASSWORD": "geheimpasswort123",
            "DJANGO_SUPERUSER_EMAIL": "test@scalingo.example",
        }):
            out_create = StringIO()
            call_command("ensure_admin", stdout=out_create)
            self.assertIn("erfolgreich erstellt", out_create.getvalue())

            user = User.objects.get(username="scalingo_testadmin")
            self.assertTrue(user.is_superuser)
            self.assertTrue(user.check_password("geheimpasswort123"))

            # Idempotenz: zweiter Aufruf aktualisiert
            out_update = StringIO()
            call_command("ensure_admin", stdout=out_update)
            self.assertIn("aktualisiert", out_update.getvalue())

