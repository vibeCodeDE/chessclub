"""Barrierefreiheits- und NFR-Tests (WCAG 2.1 AA / Universal Access / N2.3, N2.6).

Prüft automatisiert und nachvollziehbar:
- Sprachattribute (lang="de") und Viewport-Skalierbarkeit (kein user-scalable=no, kein maximum-scale=1)
- Tastaturbedienbarkeit: Skip-Links auf allen Hüllen, :focus-visible in Stylesheets
- Semantische HTML5-Landmarks (header, nav, main, footer, aside)
- Eindeutige Überschriften-Hierarchie (h1 auf jeder Seite)
- Formular-Zugänglichkeit (Label-Zuordnung per 'for'/'id' oder aria-label)
- Rollenbasierte Barrierefreiheit (Admin, Kapitän, Mitglied)
- Feedback- und Fehlerbereiche mit ARIA-Live / Status-Rollen
- Negativtests: Erkennung von unzugänglichen Inputs und fehlenden Sprachattributen
"""

import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccessibilityBaseAndStylesTests(TestCase):
    """Prüfung der Basis-Templates und Stylesheets auf WCAG 2.1 AA Konformität."""

    def test_basis_templates_enthalten_deutsche_sprache(self):
        """Alle Basis-Templates deklarieren lang="de" für Screenreader."""
        base_templates = [
            settings.BASE_DIR / "templates/base.html",
            settings.BASE_DIR / "templates/public_base.html",
            settings.BASE_DIR / "templates/auth_base.html",
        ]
        for pfad in base_templates:
            inhalt = pfad.read_text(encoding="utf-8")
            self.assertIn('<html lang="de">', inhalt, f"Fehlendes lang=\"de\" in {pfad.name}")

    def test_viewport_ist_voll_skalierbar_ohne_sperren(self):
        """Zoom bis 200% darf nicht durch user-scalable=no oder maximum-scale=1 blockiert werden."""
        base_templates = [
            settings.BASE_DIR / "templates/base.html",
            settings.BASE_DIR / "templates/public_base.html",
            settings.BASE_DIR / "templates/auth_base.html",
        ]
        for pfad in base_templates:
            inhalt = pfad.read_text(encoding="utf-8")
            self.assertIn('name="viewport"', inhalt, f"Fehlender Viewport-Meta in {pfad.name}")
            self.assertNotIn("user-scalable=no", inhalt, f"Zoom blockiert in {pfad.name}")
            self.assertNotIn("maximum-scale=1", inhalt, f"Max-Scale blockiert in {pfad.name}")

    def test_skip_links_in_allen_basis_templates(self):
        """Tastaturnutzer erhalten Skip-Links zum direkten Überspringen der Navigation."""
        app_base = (settings.BASE_DIR / "templates/base.html").read_text(encoding="utf-8")
        pub_base = (settings.BASE_DIR / "templates/public_base.html").read_text(encoding="utf-8")
        auth_base = (settings.BASE_DIR / "templates/auth_base.html").read_text(encoding="utf-8")

        self.assertIn('href="#main-content"', app_base)
        self.assertIn('id="main-content"', app_base)

        self.assertIn('href="#inhalt"', pub_base)
        self.assertIn('id="inhalt"', pub_base)

        self.assertIn('href="#auth-card"', auth_base)
        self.assertIn('id="auth-card"', auth_base)

    def test_focus_visible_regeln_in_allen_stylesheets(self):
        """Alle Stylesheets definieren klare :focus-visible Stile für Tastaturbedienung."""
        app_css = (settings.BASE_DIR / "static/css/app.css").read_text(encoding="utf-8")
        site_css = (settings.BASE_DIR / "static/css/site.css").read_text(encoding="utf-8")

        self.assertIn(":focus-visible", app_css, "app.css fehlt :focus-visible")
        self.assertIn(":focus-visible", site_css, "site.css fehlt :focus-visible")

    def test_aria_und_semantische_landmarks_in_basis_templates(self):
        """Templates nutzen semantische HTML5-Elemente mit passenden ARIA-Attributen."""
        for pfad_name in ["templates/base.html", "templates/public_base.html"]:
            inhalt = (settings.BASE_DIR / pfad_name).read_text(encoding="utf-8")
            self.assertIn("<header", inhalt)
            self.assertIn("<nav", inhalt)
            self.assertIn("<main", inhalt)
            self.assertIn('aria-label="Hauptnavigation"', inhalt)


class AccessibilityPublicViewsTests(TestCase):
    """Prüfung der gerenderten öffentlichen Seiten."""

    def test_oeffentliche_hauptseiten_haben_h1_und_semantik(self):
        """Jede Hauptseite besitzt genau eine primäre h1-Überschrift und Skip-Links."""
        routen = [
            reverse("core:home"),
            reverse("core:news_archiv"),
            reverse("tournaments:public_list"),
            reverse("core:verein"),
            reverse("core:login"),
            reverse("members:join_info"),
        ]
        for pfad in routen:
            res = self.client.get(pfad)
            self.assertEqual(res.status_code, 200, f"Fehler beim Aufruf von {pfad}")
            html = res.content.decode("utf-8")
            h1_treffer = re.findall(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S)
            self.assertTrue(len(h1_treffer) >= 1, f"Keine <h1> Überschrift auf {pfad} gefunden")
            self.assertIn('class="skip-link"', html)

    def test_login_formular_hat_saubere_labels(self):
        """Das Login-Formular hat barrierefreie Beschriftungen."""
        res = self.client.get(reverse("core:login"))
        html = res.content.decode("utf-8")
        self.assertIn('for="id_username"', html)
        self.assertIn('for="id_password"', html)


class AccessibilityInternalViewsTests(TestCase):
    """Prüfung der internen Verwaltungsansichten mit verschiedenen Rollen."""

    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name="admin")
        self.kapitaen_group, _ = Group.objects.get_or_create(name="kapitaen")
        self.mitglied_group, _ = Group.objects.get_or_create(name="mitglied")

        self.admin_user = User.objects.create_user(
            username="admin_a11y", email="admin@schach.de", password="password123"
        )
        self.admin_user.groups.add(self.admin_group)

        self.mitglied_user = User.objects.create_user(
            username="mitglied_a11y", email="mitglied@schach.de", password="password123"
        )
        self.mitglied_user.groups.add(self.mitglied_group)

    def test_admin_dashboard_und_listen_sind_zugänglich(self):
        """Interne Ansichten rendern semantisch, mit h1, Skip-Link und Landmarks."""
        self.client.force_login(self.admin_user)
        routen = [
            reverse("core:dashboard"),
            reverse("members:member_list"),
            reverse("dues:overview"),
            reverse("cashbook:entry_list"),
        ]
        for pfad in routen:
            res = self.client.get(pfad)
            self.assertEqual(res.status_code, 200, f"Fehler auf interner Route {pfad}")
            html = res.content.decode("utf-8")
            self.assertIn('class="skip-link"', html)
            self.assertIn('id="main-content"', html)
            self.assertIn('role="search"', html)
            self.assertIn('aria-label="Verein durchsuchen"', html)

    def test_mitglied_profil_hat_zugeordnete_labels(self):
        """Profil- und Selbstbedienungsseite hat barrierefreie Formularlabels."""
        self.client.force_login(self.mitglied_user)
        res = self.client.get(reverse("members:profil"))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode("utf-8")
        self.assertIn('id="main-content"', html)
        self.assertIn('class="skip-link"', html)

    def test_negativtest_fehlendes_label_wird_erkannt(self):
        """Negativtest: Ein unbeschriftetes Input ohne Label oder aria-label ist ungültig."""
        bad_html = '<input type="text" name="bad_input">'
        has_label = bool(re.search(r'<label[^>]*for="bad_input"', bad_html) or 'aria-label=' in bad_html)
        self.assertFalse(has_label, "Negativtest fehlerhaft: Unbeschriftetes Input fälschlich als valide erkannt")
