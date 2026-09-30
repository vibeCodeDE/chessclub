"""Öffentlicher Bereich: Designsprache, neue Seiten und Randfälle.

Die Design-Referenz (Next.js-ZIP) liefert nur die Gestaltung; diese Tests sichern
ab, dass die Umsetzung in Django vollständig und ohne Fremdquellen bleibt.
"""

import pathlib
import re

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from comms.models import NewsPost
from tournaments.models import Tournament

PUBLIC_TEMPLATES = [
    "templates/public_base.html",
    "templates/auth_base.html",
    "templates/produkt_base.html",
    "templates/404.html",
    "templates/includes/public_field.html",
    "core/templates/core/home.html",
    "core/templates/core/news_archiv.html",
    "core/templates/core/news_detail.html",
    "core/templates/core/verein.html",
    "core/templates/core/produkt.html",
    "core/templates/core/rechtliches.html",
    "core/templates/core/offline.html",
    "core/templates/registration/login.html",
    "core/templates/registration/zwei_faktor.html",
    "core/templates/registration/password_reset_form.html",
    "core/templates/registration/password_reset_done.html",
    "core/templates/registration/password_reset_confirm.html",
    "core/templates/registration/password_reset_complete.html",
    "tournaments/templates/tournaments/public_list.html",
    "tournaments/templates/tournaments/public_detail.html",
    "members/templates/members/join_info.html",
]


class DesignSystemTests(TestCase):
    """Das öffentliche Design-System bleibt vollständig und eigenständig."""

    def test_jede_genutzte_klasse_ist_in_site_css_definiert(self):
        css = (settings.BASE_DIR / "static/css/site.css").read_text(encoding="utf-8")
        definiert = set(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", css))
        fehlend = {}
        for pfad in PUBLIC_TEMPLATES:
            inhalt = (settings.BASE_DIR / pfad).read_text(encoding="utf-8")
            # Template-Logik entfernen, damit keine Tags als Klassen gelten.
            inhalt = re.sub(r"\{%-?.*?-?%\}", " ", inhalt, flags=re.S)
            for attr in re.findall(r'class="([^"]*)"', inhalt):
                for klasse in attr.split():
                    if any(z in klasse for z in "{}."):
                        continue  # dynamische Klassen (z. B. {{ message.tags }})
                    if klasse not in definiert:
                        fehlend.setdefault(klasse, set()).add(pfad)
        self.assertEqual(fehlend, {}, f"Klassen ohne Regel in site.css: {fehlend}")

    def test_oeffentliche_templates_laden_nur_site_css(self):
        """Internes Design (app.css) und öffentliches Design bleiben getrennt."""
        for pfad in PUBLIC_TEMPLATES:
            with self.subTest(template=pfad):
                inhalt = (settings.BASE_DIR / pfad).read_text(encoding="utf-8")
                self.assertNotRegex(inhalt, r'<link[^>]+app\.css')
                self.assertNotRegex(inhalt, r'<link[^>]+landing\.css')

    def test_oeffentliche_huellen_laden_nur_public_js(self):
        """Das Skript des öffentlichen Auftritts ist getrennt vom internen app.js."""
        for pfad in ("templates/public_base.html", "templates/auth_base.html"):
            with self.subTest(template=pfad):
                inhalt = (settings.BASE_DIR / pfad).read_text(encoding="utf-8")
                self.assertIn("js/public.js", inhalt)
                self.assertNotIn("js/app.js", inhalt)

    def test_public_js_bedient_die_oeffentlichen_bausteine(self):
        """Ohne app.js müssen Navigation und Ladebalken eigenständig funktionieren."""
        js = (settings.BASE_DIR / "static/js/public.js").read_text(encoding="utf-8")
        for merkmal in ("data-public-nav", "data-public-nav-toggle", "data-loading-bar", "data-no-loading"):
            with self.subTest(merkmal=merkmal):
                self.assertIn(merkmal, js)

    def test_public_js_bindet_keinen_internen_code_ein(self):
        """Negativtest: public.js greift nicht auf interne Bausteine zurück."""
        js = (settings.BASE_DIR / "static/js/public.js").read_text(encoding="utf-8")
        for intern in ("data-sidebar", "data-ajax", "data-autosave", "App.post"):
            with self.subTest(intern=intern):
                self.assertNotIn(intern, js)

    def test_site_css_hat_balancierte_klammern(self):
        css = (settings.BASE_DIR / "static/css/site.css").read_text(encoding="utf-8")
        self.assertEqual(css.count("{"), css.count("}"))

    def test_keine_fremdquellen_im_ausgelieferten_html(self):
        """PRD N1.1: keine CDNs, keine externen Schriften oder Skripte."""
        for url in ["/", "/aktuelles/", "/turniere/", "/verein/", "/mitglied-werden/", "/anmelden/", "/offline/", "/produkt/", "/impressum/", "/datenschutz/"]:
            with self.subTest(url=url):
                inhalt = self.client.get(url).content.decode()
                self.assertNotRegex(inhalt, r'(?:href|src)="https?://')
                self.assertNotIn("@import", inhalt)

    def test_alte_klassen_der_referenz_bleiben_verwendet(self):
        """Stichprobe: zentrale Bausteine der Designsprache sind im Einsatz."""
        NewsPost.objects.create(
            titel="Bericht", text="Text", kategorie="Verein", veroeffentlicht=True
        )
        for url, klassen in [
            ("/", ["site-header", "hero-grid", "weekly-band", "stats-grid", "news-row", "site-footer"]),
            ("/aktuelles/", ["page-intro", "filter-bar", "index-aside"]),
        ]:
            with self.subTest(url=url):
                inhalt = self.client.get(url).content.decode()
                for klasse in klassen:
                    self.assertIn(klasse, inhalt)


class VereinsseiteTests(TestCase):
    """Neue öffentliche Seite „Der Verein“ (PRD S2.2)."""

    def test_vereinsseite_ist_oeffentlich_erreichbar(self):
        response = self.client.get("/verein/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Der Verein")
        self.assertContains(response, "Trainieren")

    def test_vereinsseite_ist_in_navigation_und_footer_verlinkt(self):
        inhalt = self.client.get("/").content.decode()
        self.assertIn(reverse("core:verein"), inhalt)

    def test_leere_vereinsdaten_werden_ausgeblendet(self):
        """Ohne gepflegte Vereinsdaten erscheinen keine erfundenen Angaben."""
        with override_settings(CLUB_YOUTH_HOURS="", CLUB_FOUNDED=""):
            inhalt = self.client.get("/verein/").content.decode()
        self.assertNotIn("Jugendtraining", inhalt)
        self.assertNotIn("JAHRE VEREINSGESCHICHTE", inhalt)

    def test_ohne_treffpunkt_bleibt_ein_ehrlicher_hinweis(self):
        """Negativtest: kein erfundener Spielort, aber ein sichtbarer Fallback."""
        with override_settings(CLUB_ROOM=""):
            inhalt = self.client.get("/verein/").content.decode()
        self.assertIn("UNSER TREFFPUNKT", inhalt)
        self.assertIn("erfährst du per E-Mail", inhalt)

    def test_gepflegter_treffpunkt_erscheint_auf_allen_oeffentlichen_seiten(self):
        with override_settings(CLUB_ROOM="Vereinsheim Musterstadt"):
            for url in ["/", "/verein/", "/mitglied-werden/"]:
                with self.subTest(url=url):
                    self.assertContains(self.client.get(url), "Vereinsheim Musterstadt")

    def test_jahreszahl_kommt_aus_den_settings(self):
        with override_settings(CLUB_FOUNDED="1924"):
            inhalt = self.client.get("/").content.decode()
        self.assertIn("gegründet 1924", inhalt)


class AktuellesFilterTests(TestCase):
    """Kategoriefilter im Archiv (Design-Vorgabe aus der Referenz)."""

    def setUp(self):
        NewsPost.objects.create(
            titel="Ligabericht", text="Text A", kategorie="Spielbetrieb", veroeffentlicht=True, veroeffentlicht_am="2026-01-05T10:00:00Z"
        )
        NewsPost.objects.create(
            titel="Jugendturnier", text="Text B", kategorie="Jugend", veroeffentlicht=True, veroeffentlicht_am="2026-02-05T10:00:00Z"
        )
        NewsPost.objects.create(titel="Entwurf", text="Text C", kategorie="Jugend", veroeffentlicht=False)

    def test_alle_beitraege_ohne_filter(self):
        inhalt = self.client.get("/aktuelles/").content.decode()
        self.assertIn("Ligabericht", inhalt)
        self.assertIn("Jugendturnier", inhalt)
        self.assertNotIn("Entwurf", inhalt)

    def test_filter_nach_kategorie(self):
        inhalt = self.client.get("/aktuelles/?kategorie=Jugend").content.decode()
        self.assertIn("Jugendturnier", inhalt)
        self.assertNotIn("Ligabericht", inhalt)

    def test_unbekannte_kategorie_zeigt_alle_beitraege(self):
        """Negativtest: manipulierter Parameter darf nichts verstecken."""
        inhalt = self.client.get("/aktuelles/?kategorie=GibtEsNicht").content.decode()
        self.assertIn("Ligabericht", inhalt)
        self.assertIn("Jugendturnier", inhalt)

    def test_entwurf_bleibt_auch_mit_filter_verborgen(self):
        inhalt = self.client.get("/aktuelles/?kategorie=Jugend").content.decode()
        self.assertNotIn("Entwurf", inhalt)


class FehlerseitenTests(TestCase):
    def test_404_nutzt_die_oeffentliche_designsprache(self):
        response = self.client.get("/gibt-es-nicht/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Dieser Zug ging", status_code=404)
        self.assertContains(response, "site-footer", status_code=404)

    def test_404_bietet_weg_zurueck(self):
        response = self.client.get("/gibt-es-nicht/")
        self.assertContains(response, 'href="/"', status_code=404)


class TurnierDarstellungTests(TestCase):
    """Die öffentlichen Turnierseiten zeigen echte Daten im neuen Design."""

    def setUp(self):
        self.turnier = Tournament.objects.create(
            name="Herbst-Open",
            datum="2026-11-14",
            ort="Vereinsheim",
            oeffentlich=True,
            status=Tournament.Status.ANMELDUNG,
            beschreibung="Offenes Turnier über fünf Runden.",
        )

    def test_liste_zeigt_termine_und_anmeldestatus(self):
        inhalt = self.client.get("/turniere/").content.decode()
        self.assertIn("Herbst-Open", inhalt)
        self.assertIn("ANMELDUNG OFFEN", inhalt)
        self.assertIn("Vereinsheim", inhalt)

    def test_detail_zeigt_eckdaten_und_anmeldeformular(self):
        inhalt = self.client.get(f"/turniere/{self.turnier.pk}/").content.decode()
        self.assertIn("Die Eckdaten", inhalt)
        self.assertIn("Sichere dir deinen", inhalt)
        self.assertIn('name="name"', inhalt)

    def test_geschlossene_anmeldung_zeigt_kein_formular(self):
        """Negativtest: ohne offene Anmeldung kein Anmeldefeld."""
        self.turnier.status = Tournament.Status.BEENDET
        self.turnier.save()
        inhalt = self.client.get(f"/turniere/{self.turnier.pk}/").content.decode()
        self.assertIn("Anmeldung geschlossen", inhalt)
        self.assertNotIn('name="twz"', inhalt)

    def test_nicht_oeffentliches_turnier_bleibt_404(self):
        geheim = Tournament.objects.create(name="Intern", datum="2026-12-01", oeffentlich=False)
        self.assertEqual(self.client.get(f"/turniere/{geheim.pk}/").status_code, 404)


class BildbestandTests(TestCase):
    """Die öffentlichen Seiten verweisen nur auf vorhandene lokale Bilder."""

    def test_verwendete_bilder_existieren(self):
        referenziert = set()
        for pfad in PUBLIC_TEMPLATES:
            inhalt = (settings.BASE_DIR / pfad).read_text(encoding="utf-8")
            referenziert |= set(re.findall(r"static 'img/([^']+)'", inhalt))
        self.assertTrue(referenziert, "Keine Bilder referenziert – Test wäre wertlos.")
        for datei in sorted(referenziert):
            with self.subTest(bild=datei):
                ziel = pathlib.Path(settings.BASE_DIR) / "static/img" / datei
                self.assertTrue(ziel.exists(), f"{datei} fehlt in static/img/")
                self.assertGreater(ziel.stat().st_size, 10_000, f"{datei} wirkt leer")
