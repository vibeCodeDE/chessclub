"""PWA: Manifest, Service Worker, Icons und Offline-Seite (T23)."""

import json
import pathlib

from django.contrib.staticfiles import finders
from django.test import TestCase


def static_datei(relativer_pfad):
    """Liest eine Datei aus dem static-Verzeichnis (Testclient liefert keine Statics)."""
    treffer = finders.find(relativer_pfad)
    assert treffer, f"{relativer_pfad} nicht gefunden"
    return pathlib.Path(treffer)


class PwaTests(TestCase):
    def test_manifest_ist_gueltig(self):
        daten = json.loads(static_datei("manifest.webmanifest").read_text(encoding="utf-8"))
        for schluessel in ("name", "short_name", "start_url", "display", "icons", "theme_color"):
            self.assertIn(schluessel, daten)
        self.assertEqual(daten["display"], "standalone")
        self.assertEqual(daten["lang"], "de")

    def test_manifest_icons_existieren_mit_mindestens_zwei_groessen(self):
        icons = json.loads(static_datei("manifest.webmanifest").read_text(encoding="utf-8"))["icons"]
        groessen = {icon["sizes"] for icon in icons}
        self.assertIn("192x192", groessen)
        self.assertIn("512x512", groessen)
        for icon in icons:
            self.assertTrue(
                finders.find(icon["src"].removeprefix("/static/")),
                f"Icon {icon['src']} fehlt im static-Verzeichnis",
            )

    def test_service_worker_wird_unter_wurzel_ausgeliefert(self):
        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response["Content-Type"])
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        inhalt = response.content.decode()
        self.assertIn("OFFLINE_URL", inhalt)
        self.assertIn("/offline/", inhalt)

    def test_offline_seite_ladbar(self):
        response = self.client.get("/offline/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Zurzeit offline")

    def test_layouts_binden_manifest_und_theme_color_ein(self):
        for url in ("/", "/anmelden/", "/turniere/"):
            with self.subTest(url=url):
                inhalt = self.client.get(url).content.decode()
                self.assertIn('rel="manifest"', inhalt)
                self.assertIn('name="theme-color"', inhalt)
                self.assertIn("apple-touch-icon", inhalt)

    def test_service_worker_wird_registriert(self):
        # Der interne Bereich lädt app.js, die öffentlichen Seiten public.js –
        # beide registrieren den Service Worker (PRD N2.7).
        for datei in ("js/public.js", "js/app.js"):
            with self.subTest(datei=datei):
                inhalt = static_datei(datei).read_text(encoding="utf-8")
                self.assertIn("serviceWorker", inhalt)
                self.assertIn('register("/sw.js"', inhalt)
