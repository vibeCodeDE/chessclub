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

    def test_vereinsstartseite_bleibt_unveraendert(self):
        """„/“ zeigt die Vereinsseite, die Produkt-Landingpage liegt unter „/produkt/“."""
        vereinsseite = self.client.get("/").content.decode()
        produktseite = self.client.get("/produkt/").content.decode()
        verkaufssatz = "Vereinsverwaltung, die Ihr Vorstand gerne benutzt."
        self.assertIn(settings.CLUB_SHORT, vereinsseite)
        self.assertIn(verkaufssatz, produktseite)
        self.assertNotIn(verkaufssatz, vereinsseite)
