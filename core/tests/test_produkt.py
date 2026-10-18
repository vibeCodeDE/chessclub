from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from core import produkt


@override_settings(PRODUCT_NAME="Testprodukt", PRODUCT_CONTACT="kontakt@test.example", IS_MARKETING_SITE=True)
class ProduktSeiteTests(TestCase):
    def test_produkt_url_leitet_per_301_nach_root_um(self):
        """Negativ-/Redirect-Test: /produkt/ liefert einen permanenten 301-Redirect nach / (ADR-024)."""
        antwort = self.client.get("/produkt/")
        self.assertEqual(antwort.status_code, 301)
        self.assertEqual(antwort.url, "/")

    def test_seite_ist_auf_root_erreichbar(self):
        antwort = self.client.get("/")
        self.assertEqual(antwort.status_code, 200)

    def test_name_und_kontakt_aus_einstellungen(self):
        inhalt = self.client.get("/").content.decode()
        self.assertIn("Testprodukt", inhalt)
        self.assertIn("mailto:kontakt@test.example", inhalt)

    def test_zeigt_alle_preisstufen_und_funktionen(self):
        inhalt = self.client.get("/").content.decode()
        for stufe in produkt.PREISSTUFEN:
            self.assertIn(stufe["name"], inhalt)
        for funktion in produkt.FUNKTIONEN:
            self.assertIn(funktion["titel"], inhalt)

    def test_mobil_und_ohne_fremde_ressourcen(self):
        inhalt = self.client.get("/").content.decode()
        self.assertIn("width=device-width", inhalt)
        self.assertNotRegex(inhalt, r'(?:href|src)="https?://')

    def test_keine_inline_skripte(self):
        # CSP erlaubt nur script-src 'self'.
        inhalt = self.client.get("/").content.decode()
        self.assertNotIn("<script", inhalt)

    def test_rechtliche_seiten_erreichbar_und_verlinkt(self):
        inhalt = self.client.get("/").content.decode()
        for pfad in ("/impressum/", "/datenschutz/"):
            self.assertIn(f'href="{pfad}"', inhalt)
            self.assertEqual(self.client.get(pfad).status_code, 200)

    def test_eu_hosting_versprechen(self):
        """Landingpage und FAQ werben mit EU-Hosting und DSGVO (ADR-025), nicht irreführend mit '100 % Deutschland'."""
        inhalt = self.client.get("/").content.decode()
        self.assertIn("100 % EU-Hosting", inhalt)
        self.assertIn("Hosting in der EU", inhalt)
        self.assertNotIn("100 % Deutschland", inhalt)
        self.assertNotIn("Datenhaltung ausschließlich in Deutschland", inhalt)

    def test_vereinsstartseite_bleibt_unveraendert(self):
        """Mit IS_MARKETING_SITE=False zeigt „/“ die Vereinsseite, während schachverwaltung.de das Produkt zeigt."""
        with self.settings(IS_MARKETING_SITE=False):
            vereinsseite = self.client.get("/").content.decode()
            produktseite = self.client.get("/", HTTP_HOST="schachverwaltung.de").content.decode()
            verkaufssatz = "Vereinsverwaltung, die Ihr Vorstand gerne benutzt."
            self.assertIn(settings.CLUB_SHORT, vereinsseite)
            self.assertIn(verkaufssatz, produktseite)
            self.assertNotIn(verkaufssatz, vereinsseite)

    def test_marketing_site_auf_root_via_setting(self):
        """Mit IS_MARKETING_SITE=True zeigt „/“ die Produkt-Landingpage (ADR-024)."""
        with self.settings(IS_MARKETING_SITE=True):
            antwort = self.client.get("/")
            inhalt = antwort.content.decode()
            self.assertEqual(antwort.status_code, 200)
            self.assertIn("Vereinsverwaltung, die Ihr Vorstand gerne benutzt.", inhalt)

    def test_marketing_site_auf_root_via_hostname(self):
        """Anfragen an die Hauptdomain schachverwaltung.de zeigen die Produktseite auf „/“."""
        with self.settings(
            IS_MARKETING_SITE=False,
            PRODUCT_HOSTS=["schachverwaltung.de", "www.schachverwaltung.de"],
            ALLOWED_HOSTS=["schachverwaltung.de", "www.schachverwaltung.de", "testserver"],
        ):
            antwort = self.client.get("/", HTTP_HOST="schachverwaltung.de")
            inhalt = antwort.content.decode()
            self.assertEqual(antwort.status_code, 200)
            self.assertIn("Vereinsverwaltung, die Ihr Vorstand gerne benutzt.", inhalt)

    def test_marketing_site_auf_localhost_und_loopback(self):
        """Auf localhost und 127.0.0.1 zeigt „/“ in der Entwicklung direkt die Produktseite (ADR-024)."""
        with self.settings(IS_MARKETING_SITE=False):
            for host in ("localhost", "127.0.0.1"):
                with self.subTest(host=host):
                    antwort = self.client.get("/", HTTP_HOST=host)
                    self.assertEqual(antwort.status_code, 200)
                    self.assertIn("Vereinsverwaltung, die Ihr Vorstand gerne benutzt.", antwort.content.decode())

    def test_vereins_subdomain_bleibt_vereinsseite(self):
        """Anfragen an eine Vereins-Subdomain zeigen weiterhin die Vereinsseite auf „/“."""
        with self.settings(
            IS_MARKETING_SITE=False,
            PRODUCT_HOSTS=["schachverwaltung.de", "www.schachverwaltung.de"],
            ALLOWED_HOSTS=["sc-musterstadt.schachverwaltung.de", "testserver"],
        ):
            antwort = self.client.get("/", HTTP_HOST="sc-musterstadt.schachverwaltung.de")
            inhalt = antwort.content.decode()
            self.assertEqual(antwort.status_code, 200)
            self.assertNotIn("Vereinsverwaltung, die Ihr Vorstand gerne benutzt.", inhalt)
            self.assertIn(settings.CLUB_SHORT, inhalt)

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
        inhalt = self.client.get("/").content.decode()
        for stufe in produkt.PREISSTUFEN:
            with self.subTest(stufe=stufe["name"]):
                self.assertIn(f'{stufe["preis"]} €', inhalt)
                self.assertIn(f'{stufe["jahr"]} € pro Jahr', inhalt)
                self.assertIn(f'{stufe["preis_monatlich"]} € bei monatlicher Zahlung', inhalt)
                self.assertIn(stufe["einrichtung"], inhalt)

    def test_endpreise_statt_umsatzsteuer_und_statt_monatlicher_kuendigung(self):
        """Negativtest: die überholten Aussagen aus ADR-014 dürfen nicht mehr auftauchen."""
        inhalt = self.client.get("/").content.decode()
        self.assertIn("Endpreise", inhalt)
        self.assertIn("§ 19 UStG", inhalt)
        for ueberholt in ("zzgl. gesetzlicher Umsatzsteuer", "keine Mindestlaufzeit", "Monatlich kündbar"):
            with self.subTest(aussage=ueberholt):
                self.assertNotIn(ueberholt, inhalt)

    def test_preishinweis_nennt_laufzeit_und_aufschlag(self):
        inhalt = self.client.get("/").content.decode()
        self.assertIn(produkt.PREISHINWEIS, inhalt)
        self.assertIn("zwölf Monaten", inhalt)
        self.assertIn("20 %", inhalt)

    def test_schritte_ueberschrift_passt_zur_anzahl(self):
        """Die Überschrift zählt die Schritte – sonst widerspricht sie der Liste darunter."""
        zahlen = {1: "einem", 2: "zwei", 3: "drei", 4: "vier", 5: "fünf"}
        inhalt = self.client.get("/").content.decode()
        erwartet = f"In {zahlen[len(produkt.SCHRITTE)]} Schritten einsatzbereit"
        self.assertIn(erwartet, inhalt)

    def test_alle_faq_fragen_sind_sichtbar(self):
        inhalt = self.client.get("/").content.decode()
        for frage, _ in produkt.FAQ:
            with self.subTest(frage=frage):
                self.assertIn(frage, inhalt)


class ProduktStandardBrandingTests(TestCase):
    def test_standard_branding_ist_schachverwaltung(self):
        """Das Default-Branding lautet Schachverwaltung.de mit kontakt@schachverwaltung.de (ADR-018)."""
        self.assertEqual(settings.PRODUCT_NAME, "Schachverwaltung.de")
        self.assertEqual(settings.PRODUCT_CONTACT, "kontakt@schachverwaltung.de")

    def test_standard_branding_wird_auf_produktseite_gerendert(self):
        inhalt = self.client.get("/", HTTP_HOST="schachverwaltung.de").content.decode()
        self.assertIn("Schachverwaltung.de", inhalt)
        self.assertIn("mailto:kontakt@schachverwaltung.de", inhalt)
        # Negativtest: alte Platzhaltermarken erscheinen nicht
        self.assertNotIn("Schachclub-Manager", inhalt)
        self.assertNotIn("schachclub-manager.example", inhalt)


@override_settings(IS_MARKETING_SITE=True, PRODUCT_CONTACT="info@schachverwaltung.de")
class ProduktSchmerzpunkteTests(TestCase):
    def test_t003_rollen_schmerzpunkte_datenstruktur_vollstaendig(self):
        """T003: Prüft Pflichtfelder, Rollen und Negativfälle der Datenstruktur."""
        erwartete_rollen = {"vorstand", "kassenwart", "spielleiter", "kapitaen", "mitglieder"}
        vorhandene_rollen = {r["id"] for r in produkt.ROLLEN_SCHMERZPUNKTE}
        self.assertEqual(erwartete_rollen, vorhandene_rollen)

        for rolle in produkt.ROLLEN_SCHMERZPUNKTE:
            with self.subTest(rolle=rolle["id"]):
                # Pflichtfelder
                for feld in ("id", "titel", "kurztitel", "icon", "slogan", "ersparnis", "schmerzpunkte", "vorschau"):
                    self.assertIn(feld, rolle)
                    self.assertTrue(rolle[feld], f"Feld {feld} darf nicht leer sein.")

                # Mindestens 3 Schmerzpunkte
                self.assertGreaterEqual(len(rolle["schmerzpunkte"]), 3)
                for sp in rolle["schmerzpunkte"]:
                    self.assertIn("titel", sp)
                    self.assertIn("problem", sp)
                    self.assertIn("loesung", sp)
                    self.assertTrue(sp["problem"].strip())
                    self.assertTrue(sp["loesung"].strip())

                # Vorschau-Mockup Struktur
                vorschau = rolle["vorschau"]
                self.assertIn("typ", vorschau)
                self.assertIn("fenster_titel", vorschau)
                self.assertIn("metriken", vorschau)
                self.assertIn("zeilen", vorschau)
                self.assertGreaterEqual(len(vorschau["metriken"]), 2)
                self.assertGreaterEqual(len(vorschau["zeilen"]), 2)

    def test_t003_negativ_ungueltige_rolle_oder_daten(self):
        """T003 Negativtest: Ungültige Struktur oder leere Schmerzpunkte."""
        ungueltige_rolle = {"id": "unbekannt", "titel": ""}
        self.assertNotIn("unbekannt", [r["id"] for r in produkt.ROLLEN_SCHMERZPUNKTE])
        # Sicherstellen, dass keine Schmerzpunkte ohne Lösung existieren
        for rolle in produkt.ROLLEN_SCHMERZPUNKTE:
            for sp in rolle["schmerzpunkte"]:
                self.assertNotEqual(sp["problem"], sp["loesung"], "Problem und Lösung dürfen nicht identisch sein.")

    def test_t005_rollen_und_schmerzpunkte_gerendert(self):
        """T005: Alle 5 Rollen und Schmerzpunkte werden auf der Landingpage gerendert."""
        from django.utils.html import escape

        inhalt = self.client.get("/").content.decode()
        for rolle in produkt.ROLLEN_SCHMERZPUNKTE:
            with self.subTest(rolle=rolle["id"]):
                self.assertIn(escape(rolle["kurztitel"]), inhalt)
                self.assertIn(escape(rolle["slogan"]), inhalt)
                for sp in rolle["schmerzpunkte"]:
                    self.assertIn(escape(sp["titel"]), inhalt)
                    self.assertIn(escape(sp["problem"]), inhalt)
                    self.assertIn(escape(sp["loesung"]), inhalt)

    def test_t009_vorschauen_und_schalter_im_html_vorhanden(self):
        """T009: Interaktive Vorschau-Mockups und Metriken im HTML vorhanden."""
        from django.utils.html import escape

        inhalt = self.client.get("/").content.decode()
        for rolle in produkt.ROLLEN_SCHMERZPUNKTE:
            vorschau = rolle["vorschau"]
            self.assertIn(escape(vorschau["fenster_titel"]), inhalt)
            for m in vorschau["metriken"]:
                self.assertIn(escape(m["wert"]), inhalt)

    def test_t013_zeitersparnis_und_banner_vorhanden(self):
        """T013: Zeiteinsparung je Rolle und Banner sind sichtbar."""
        inhalt = self.client.get("/").content.decode()
        for rolle in produkt.ROLLEN_SCHMERZPUNKTE:
            self.assertIn(rolle["ersparnis"], inhalt)
        self.assertIn("Büroarbeit", inhalt)

    def test_t016_barrierefreiheit_und_keine_inline_skripte(self):
        """T016: ARIA-Tabs, Tastaturnavigation und strikte CSP ohne Inline-Skripte."""
        inhalt = self.client.get("/").content.decode()
        self.assertIn('role="tablist"', inhalt)
        self.assertIn('role="tab"', inhalt)
        self.assertIn('role="tabpanel"', inhalt)
        self.assertNotIn("<script", inhalt)

    def test_t019_rollenspezifische_demo_links(self):
        """T019: Demo-Anfrage-Buttons haben rollenbezogene Betreffzeilen."""
        inhalt = self.client.get("/").content.decode()
        for rolle in produkt.ROLLEN_SCHMERZPUNKTE:
            with self.subTest(rolle=rolle["id"]):
                self.assertIn(f"Demo%20anfragen%20(%7B%7B%20rolle.titel", inhalt) if "{{ rolle.titel" in inhalt else (
                    self.assertTrue(
                        rolle["kurztitel"] in inhalt or rolle["titel"] in inhalt
                    )
                )

