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

    def test_preisstufen_sind_vollstaendig_und_stimmig(self):
        """Jede Stufe nennt Jahres-, Monats- und Einrichtungspreis; die Zahlen passen zusammen."""
        for stufe in produkt.PREISSTUFEN:
            with self.subTest(stufe=stufe["name"]):
                for feld in ("preis", "jahr", "preis_monatlich", "einrichtung", "fuer", "punkte"):
                    self.assertIn(feld, stufe)
                preis, jahr, monatlich = int(stufe["preis"]), int(stufe["jahr"]), int(stufe["preis_monatlich"])
                self.assertEqual(jahr, 12 * preis, "Jahrespreis muss 12 Monatspreisen entsprechen")
                verhaeltnis = monatlich / preis
                self.assertGreaterEqual(verhaeltnis, 1.15, "monatliche Zahlung braucht einen Aufschlag")
                self.assertLessEqual(verhaeltnis, 1.25)
                self.assertTrue(stufe["punkte"])

    def test_preise_und_einrichtung_sind_sichtbar(self):
        inhalt = self.client.get("/produkt/").content.decode()
        for stufe in produkt.PREISSTUFEN:
            with self.subTest(stufe=stufe["name"]):
                self.assertIn(f'{stufe["preis"]} €', inhalt)
                self.assertIn(f'{stufe["jahr"]} € pro Jahr', inhalt)
                self.assertIn(f'{stufe["preis_monatlich"]} € bei monatlicher Zahlung', inhalt)
                self.assertIn(stufe["einrichtung"], inhalt)

    def test_endpreise_statt_umsatzsteuer_und_statt_monatlicher_kuendigung(self):
        """Negativtest: die überholten Aussagen aus ADR-014 dürfen nicht mehr auftauchen."""
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertIn("Endpreise", inhalt)
        self.assertIn("§ 19 UStG", inhalt)
        for ueberholt in ("zzgl. gesetzlicher Umsatzsteuer", "keine Mindestlaufzeit", "Monatlich kündbar"):
            with self.subTest(aussage=ueberholt):
                self.assertNotIn(ueberholt, inhalt)

    def test_preishinweis_nennt_laufzeit_und_aufschlag(self):
        inhalt = self.client.get("/produkt/").content.decode()
        self.assertIn(produkt.PREISHINWEIS, inhalt)
        self.assertIn("zwölf Monaten", inhalt)
        self.assertIn("20 %", inhalt)

    def test_schritte_ueberschrift_passt_zur_anzahl(self):
        """Die Überschrift zählt die Schritte – sonst widerspricht sie der Liste darunter."""
        zahlen = {1: "einem", 2: "zwei", 3: "drei", 4: "vier", 5: "fünf"}
        inhalt = self.client.get("/produkt/").content.decode()
        erwartet = f"In {zahlen[len(produkt.SCHRITTE)]} Schritten einsatzbereit"
        self.assertIn(erwartet, inhalt)

    def test_alle_faq_fragen_sind_sichtbar(self):
        inhalt = self.client.get("/produkt/").content.decode()
        for frage, _ in produkt.FAQ:
            with self.subTest(frage=frage):
                self.assertIn(frage, inhalt)
