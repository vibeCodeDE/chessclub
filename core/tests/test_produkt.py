from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from core import produkt


@override_settings(PRODUCT_NAME="Testprodukt", PRODUCT_CONTACT="kontakt@test.example")
class ProduktSeiteTests(TestCase):
    def test_seite_ist_oeffentlich(self):
        antwort = self.client.get("/produkt/")
        self.assertEqual(antwort.status_code, 200)

    def test_name_und_kontakt_aus_einstellungen(self):
        inhalt = self.client.get(reverse("core:produkt")).content.decode()
        self.assertIn("Testprodukt", inhalt)
        self.assertIn("mailto:kontakt@test.example", inhalt)

    def test_zeigt_alle_preisstufen_und_funktionen(self):
        inhalt = self.client.get("/produkt/").content.decode()
        for stufe in produkt.PREISSTUFEN:
            self.assertIn(stufe["name"], inhalt)
        for funktion in produkt.FUNKTIONEN:
            self.assertIn(funktion["titel"], inhalt)

    def test_zeigt_abschnitte_mit_ankern(self):
        """PRD S10.3: Aufbau der Verkaufsseite mit Anker-Navigation."""
        inhalt = self.client.get("/produkt/").content.decode()
        for anker, stichwort in [
            ("funktionen", "Funktionen"),
            ("datenschutz", "Datenschutz"),
            ("preise", "Preise"),
            ("faq", "Fragen"),
            ("ablauf", "So starten Sie"),
        ]:
            self.assertIn(f'id="{anker}"', inhalt)
            self.assertIn(stichwort, inhalt)
        # Die Navigation verlinkt die vier Hauptabschnitte direkt.
        for anker in ("funktionen", "datenschutz", "preise", "faq"):
            self.assertIn(f'href="#{anker}"', inhalt)

    def test_zeigt_nutzen_rollen_und_kennzahlen(self):
        """PRD S10.3: Inhalte kommen aus core/produkt.py."""
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertIn(produkt.PROBLEM["titel"], inhalt)
        for vorher in produkt.PROBLEM["vorher"]:
            self.assertIn(vorher, inhalt)
        self.assertIn(produkt.PROBLEM["mit_uns"], inhalt)
        for rolle, text in produkt.ROLLEN:
            self.assertIn(rolle, inhalt)
            self.assertIn(text, inhalt)
        for zahl, unterzeile in produkt.KENNZAHLEN:
            self.assertIn(zahl, inhalt)
            self.assertIn(unterzeile, inhalt)

    def test_preise_sind_als_platzhalter_markiert(self):
        """PRD S10.2: Platzhalterpreise werden ehrlich gekennzeichnet."""
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertIn("Platzhalter", inhalt)
        self.assertIn(produkt.PREIS_HINWEIS, inhalt)

    def test_faq_ohne_javascript_bedienbar(self):
        """PRD S10.4: FAQ ist ein <details>-Element und funktioniert ohne Skript."""
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertIn("<details>", inhalt)
        self.assertIn("<summary>", inhalt)
        for frage, _antwort in produkt.FAQ:
            self.assertIn(frage, inhalt)

    def test_laedt_nur_das_oeffentliche_designsystem(self):
        """PRD S10.1/ADR-014: nur site.css — weder app.css noch landing.css."""
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertIn("css/site.css", inhalt)
        self.assertNotIn("css/app.css", inhalt)
        self.assertNotIn("css/landing.css", inhalt)

    def test_laedt_kein_skript(self):
        """PRD S10.4: Kein JavaScript auf der Verkaufsseite (auch nicht inline, CSP)."""
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertNotIn("<script", inhalt)

    def test_keine_vereins_navigation_auf_der_verkaufsseite(self):
        """Negativtest (S10.1): Die Verkaufsseite ist nicht die Vereinsseite."""
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertNotIn('/mitglied-werden/', inhalt)
        self.assertNotIn('/aktuelles/', inhalt)
        self.assertNotIn('aria-label="Hauptnavigation"', inhalt)

    def test_mobil_und_ohne_fremde_ressourcen(self):
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertIn("width=device-width", inhalt)
        self.assertNotRegex(inhalt, r'(?:href|src)="https?://')

    def test_keine_inline_skripte(self):
        # CSP erlaubt nur script-src 'self'.
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertNotIn("<script", inhalt)

    def test_rechtliche_seiten_erreichbar_und_verlinkt(self):
        inhalt = self.client.get("/produkt/").content.decode()
        for pfad in ("/impressum/", "/datenschutz/"):
            self.assertIn(f'href="{pfad}"', inhalt)
            self.assertEqual(self.client.get(pfad).status_code, 200)

    def test_rechtliche_seiten_im_gleichen_design(self):
        """PRD S10.1: Impressum und Datenschutz nutzen dieselbe Hülle und Designsprache."""
        for pfad in ("/impressum/", "/datenschutz/"):
            with self.subTest(pfad=pfad):
                inhalt = self.client.get(pfad).content.decode()
                self.assertIn("css/site.css", inhalt)
                self.assertNotIn("css/landing.css", inhalt)
                self.assertIn("Testprodukt", inhalt)
                self.assertIn('href="/produkt/"', inhalt)  # zurück zur Verkaufsseite
                self.assertNotIn("<script", inhalt)

    def test_landing_css_entfaellt_ersatzlos(self):
        """Negativtest (S10.4, ADR-014): Die alte Produktgestaltung ist weg."""
        self.assertFalse(
            (settings.BASE_DIR / "static/css/landing.css").exists(),
            "landing.css sollte gelöscht sein (ADR-014).",
        )
        templates = list(settings.BASE_DIR.rglob("*.html"))
        for vorlage in templates:
            with self.subTest(vorlage=str(vorlage.relative_to(settings.BASE_DIR))):
                self.assertNotIn("landing.css", vorlage.read_text(encoding="utf-8"))

    def test_vereinsstartseite_bleibt_unveraendert(self):
        """„/“ zeigt die Vereinsseite, die Produkt-Landingpage liegt unter „/produkt/“."""
        vereinsseite = self.client.get("/").content.decode()
        produktseite = self.client.get("/produkt/").content.decode()
        verkaufssatz = produkt.HERO["titel"]
        self.assertIn(settings.CLUB_SHORT, vereinsseite)
        self.assertIn(verkaufssatz, produktseite)
        self.assertNotIn(verkaufssatz, vereinsseite)
