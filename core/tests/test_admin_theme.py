"""Tests für Django Admin Theming, Dark Mode und Kontraste (WCAG 2.1 AA).

Stellt sicher:
- Vollständige Deklaration von Light Mode und Dark Mode im Admin-Stylesheet.
- Barrierefreie Farbkontraste (mindestens 4.5:1 für Fließtext, 3.0:1 für Akzente/Buttons).
- Korrekte Einbindung von admin.css in den Admin-Templates.
- Rollenbasierte Zugriffssicherung des Adminbereichs (Negativtests für unberechtigte Nutzer).
- Erkennung unzureichender Kontraste per Negativtest.
"""

import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

User = get_user_model()


def relative_luminance(hex_code: str) -> float:
    """Berechnet die relative Helligkeit eines Hex-Farbcodes gemäß WCAG 2.1."""
    hex_code = hex_code.lstrip("#")
    r, g, b = (int(hex_code[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def adjust(val: float) -> float:
        return val / 12.92 if val <= 0.03928 else ((val + 0.055) / 1.055) ** 2.4

    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    """Berechnet das Kontrastverhältnis zweier Farben gemäß WCAG 2.1."""
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class AdminThemeAndContrastTests(TestCase):
    """Prüfung der Farbwahl und Theming-Regeln für das Django Admin."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser("admin_chef", "chef@schach.de", "pass123")
        cls.mitglied = User.objects.create_user("normalo", "normalo@schach.de", "pass123")
        gruppe_mitglied, _ = Group.objects.get_or_create(name="mitglied")
        cls.mitglied.groups.add(gruppe_mitglied)

        cls.css_path = settings.BASE_DIR / "static/css/admin.css"
        cls.css_content = cls.css_path.read_text(encoding="utf-8")

    def test_admin_css_existiert_und_enthaelt_beide_modi(self):
        """Das Admin-CSS deklariert Light- und Dark-Mode-Blöcke."""
        self.assertTrue(self.css_path.exists())
        self.assertIn(':root', self.css_content)
        self.assertIn('html[data-theme="light"]', self.css_content)
        self.assertIn('html[data-theme="dark"]', self.css_content)
        self.assertIn('@media (prefers-color-scheme: dark)', self.css_content)

    def test_django_admin_variablen_werden_in_beiden_modi_harmonisiert(self):
        """Zentrale Django-Admin-Variablen werden für nahtloses Theming überschrieben."""
        for var_name in [
            "--primary",
            "--secondary",
            "--header-bg",
            "--breadcrumbs-bg",
            "--link-fg",
            "--body-bg",
            "--body-fg",
            "--body-quiet-color",
            "--border-color",
            "--darkened-bg",
            "--selected-row",
        ]:
            with self.subTest(variable=var_name):
                self.assertIn(var_name, self.css_content)

    def test_kontraste_light_mode_erfuellen_wcag_aa(self):
        """Alle primären Farbpaare im Light Mode erreichen mindestens 4.5:1."""
        paare = [
            ("#1d2b22", "#ffffff", "Text auf Karte"),
            ("#1d2b22", "#f5f8f5", "Text auf Hintergrund"),
            ("#1b382b", "#f0f5ef", "Überschrift auf dezentem Streifen"),
            ("#1b382b", "#ffffff", "Link auf Karte"),
            ("#ffffff", "#1b382b", "Weißer Text auf Waldgrün-Header/Button"),
            ("#56695b", "#ffffff", "Gedämpfter Text auf Karte"),
            ("#9e2a22", "#faeae8", "Löschlink auf rotem Hintergrund"),
        ]
        for vordergrund, hintergrund, bezeichnung in paare:
            with self.subTest(paar=bezeichnung):
                ratio = contrast_ratio(vordergrund, hintergrund)
                self.assertGreaterEqual(
                    ratio,
                    4.5,
                    f"Kontrast für '{bezeichnung}' zu niedrig: {ratio:.2f}:1 (Soll >= 4.5:1)",
                )

    def test_kontraste_dark_mode_erfuellen_wcag_aa(self):
        """Alle primären Farbpaare im Dark Mode erreichen mindestens 4.5:1."""
        paare = [
            ("#e8f0ea", "#19251e", "Heller Text auf dunkler Karte"),
            ("#e8f0ea", "#111a14", "Heller Text auf dunklem Hintergrund"),
            ("#ffffff", "#223329", "Weiße Überschrift auf dunklem Karten-Header"),
            ("#72d699", "#19251e", "Hellgrüner Link auf dunkler Karte"),
            ("#ffffff", "#2b5641", "Weißer Text auf Button"),
            ("#a3baa8", "#19251e", "Gedämpfter Text / Labels auf dunkler Karte"),
            ("#fca59f", "#3b1a18", "Löschlink auf dunklem rotem Hintergrund"),
            ("#e2ba73", "#19251e", "Goldener Akzent auf dunkler Karte"),
        ]
        for vordergrund, hintergrund, bezeichnung in paare:
            with self.subTest(paar=bezeichnung):
                ratio = contrast_ratio(vordergrund, hintergrund)
                self.assertGreaterEqual(
                    ratio,
                    4.5,
                    f"Kontrast für '{bezeichnung}' im Dark Mode zu niedrig: {ratio:.2f}:1 (Soll >= 4.5:1)",
                )

    def test_negativtest_schlechter_kontrast_wird_zuverlaessig_erkannt(self):
        """Negativtest: Ein unzureichendes Farbpaar (z. B. Hellgrau auf Weiß) wird abgewiesen."""
        schlechtes_verhaeltnis = contrast_ratio("#d0d0d0", "#ffffff")
        self.assertLess(
            schlechtes_verhaeltnis,
            4.5,
            "Negativtest fehlgeschlagen: Hellgrau auf Weiß sollte unter 4.5:1 liegen",
        )

    def test_admin_index_bindet_admin_css_ein(self):
        """Die Admin-Indexseite liefert das angepasste admin.css aus."""
        self.client.force_login(self.superuser)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin.css")
        self.assertContains(response, "Administration")

    def test_admin_login_seite_bindet_admin_css_ein(self):
        """Auch die Login-Seite des Admins bindet admin.css ein."""
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin.css")

    def test_negativtest_normales_mitglied_wird_vom_admin_abgewiesen(self):
        """Negativtest: Mitglieder ohne Staff-Berechtigung dürfen das Admin nicht betreten."""
        self.client.force_login(self.mitglied)
        response = self.client.get("/admin/")
        # Django leitet Nicht-Staff-Nutzer auf die Admin-Login-Seite um
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.headers.get("Location", ""))
