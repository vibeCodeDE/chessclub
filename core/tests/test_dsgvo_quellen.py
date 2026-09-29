"""DSGVO N1.1: keine Drittanbieter-Tracker, keine externen CDNs.

Der Test liest alle Templates, Stylesheets und Skripte und verbietet Verweise
auf fremde Hosts. Ausnahmen sind reine XML-Namensräume (SVG) und das
``otpauth://``-Schema, die keine Netzwerkverbindung auslösen.
"""

import pathlib
import re

from django.conf import settings
from django.test import SimpleTestCase

ERLAUBTE_MUSTER = (
    "http://www.w3.org",  # SVG-Namensraum (kein Abruf)
    "https://www.w3.org",
    "http://www.w3.org/2000/svg",
    "otpauth://",         # wird als Text angezeigt, nicht verlinkt
)

VERBOTENE_HOSTS = re.compile(
    r"""(?:src|href|action|url)\s*=?\s*["'(]?\s*https?://(?!(?:www\.)?w3\.org)[^\s"'()>]+""",
    re.IGNORECASE,
)


class ExterneQuellenTests(SimpleTestCase):
    def test_templates_ohne_fremde_hosts(self):
        verdaechtig = []
        for pfad in pathlib.Path(settings.BASE_DIR).rglob("*.html"):
            if "node_modules" in str(pfad) or ".venv" in str(pfad):
                continue
            inhalt = pfad.read_text(encoding="utf-8")
            for treffer in VERBOTENE_HOSTS.finditer(inhalt):
                if any(muster in treffer.group(0) for muster in ERLAUBTE_MUSTER):
                    continue
                verdaechtig.append(f"{pfad.relative_to(settings.BASE_DIR)}: {treffer.group(0)}")
        self.assertEqual(verdaechtig, [], "Externe Quellen gefunden: " + "; ".join(verdaechtig))

    def test_css_und_js_ohne_fremde_hosts(self):
        verdaechtig = []
        for ordner, endungen in ((settings.BASE_DIR / "static", (".css", ".js")),):
            for pfad in ordner.rglob("*"):
                if pfad.suffix not in endungen or "sw.js" in pfad.name:
                    # sw.js nennt nur relative Pfade, wird separat geprüft
                    continue
                inhalt = pfad.read_text(encoding="utf-8")
                for treffer in re.finditer(r"https?://(?!(?:www\.)?w3\.org)[^\s\"'()]+", inhalt):
                    verdaechtig.append(f"{pfad.name}: {treffer.group(0)}")
        self.assertEqual(verdaechtig, [], "Externe Quellen im Frontend: " + "; ".join(verdaechtig))

    def test_service_worker_cacht_nur_eigene_herkunft(self):
        inhalt = (settings.BASE_DIR / "static" / "sw.js").read_text(encoding="utf-8")
        self.assertIn("url.origin !== self.location.origin", inhalt)

    def test_keine_tracking_begriffe_im_frontend(self):
        verboten = ["google-analytics", "googletagmanager", "facebook.net", "doubleclick", "matomo", "fonts.googleapis"]
        gefunden = []
        for pfad in list(pathlib.Path(settings.BASE_DIR).rglob("*.html")) + list(
            (settings.BASE_DIR / "static").rglob("*")
        ):
            if pfad.suffix not in {".html", ".css", ".js"} or ".venv" in str(pfad):
                continue
            inhalt = pfad.read_text(encoding="utf-8", errors="ignore").lower()
            for begriff in verboten:
                if begriff in inhalt:
                    gefunden.append(f"{pfad.name}: {begriff}")
        self.assertEqual(gefunden, [], "Tracking-Reste gefunden: " + "; ".join(gefunden))

    def test_passwoerter_mit_argon2(self):
        """PRD N1.6: Passwörter verschlüsselt mit bcrypt/argon2.

        Geprüft wird die Produktivkonfiguration – die Tests selbst nutzen aus
        Laufzeitgründen einen schnellen Hasher (`config.settings_test`).
        """
        import config.settings as produktiv

        self.assertEqual(
            produktiv.PASSWORD_HASHERS[0], "django.contrib.auth.hashers.Argon2PasswordHasher",
            "Argon2 muss der erste Hasher sein (argon2-cffi in requirements.txt)",
        )
        anforderungen = (settings.BASE_DIR / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("argon2-cffi", anforderungen)

    def test_audit_protokoll_hat_keine_automatische_loeschung(self):
        """PRD N1.5: Protokolle bleiben mindestens 12 Monate erhalten."""
        from core.models import AuditLog

        feldnamen = {feld.name for feld in AuditLog._meta.fields}
        self.assertNotIn("loeschbar_ab", feldnamen)
        # Kein Standard-Manager filtert alte Einträge weg:
        self.assertEqual(str(AuditLog.objects.all().query).count("zeitpunkt__"), 0)
