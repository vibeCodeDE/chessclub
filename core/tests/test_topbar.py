"""Tests für die überarbeitete Topbar (header.topbar) in base.html."""

import re
from datetime import date
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.models import ModuleSettings
from teams.models import Season


def make_user(username, gruppe=None):
    user = User.objects.create_user(
        username=username,
        password="x",
        first_name="Max",
        last_name="Mustermann",
        email=f"{username}@example.com",
    )
    if gruppe:
        group, _ = Group.objects.get_or_create(name=gruppe)
        user.groups.add(group)
    return user


class TopbarTests(TestCase):
    """Prüft Struktur, Barrierefreiheit, Rollenunterschiede und Funktionalität der Topbar."""

    def setUp(self):
        self.admin = make_user("admin_topbar", "admin")
        self.kapitaen = make_user("kapitaen_topbar", "kapitaen")
        self.mitglied = make_user("mitglied_topbar", "mitglied")
        self.saison = Season.objects.create(
            name="2026/27",
            slug="2026-27",
            startdatum=date(2026, 9, 1),
            enddatum=date(2027, 4, 30),
            ist_aktiv=True,
        )

    def test_topbar_elemente_fuer_admin(self):
        """Admin sieht vollständige Topbar mit Breadcrumb, Suche, Saison-Link und Admin-Einträgen."""
        self.client.force_login(self.admin)
        res = self.client.get(reverse("core:dashboard"))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode("utf-8")

        # Topbar und Landmarks
        self.assertIn('class="topbar"', html)
        self.assertIn('role="search"', html)
        self.assertIn('aria-label="Verein durchsuchen"', html)
        self.assertIn('data-search-shortcut', html)

        # Breadcrumb-Hierarchie für Admin
        self.assertIn('class="breadcrumb-root"', html)
        self.assertIn("Vereinsverwaltung", html)

        # Saison-Badge mit Link zur Saisonverwaltung für Admin
        self.assertIn("2026/27", html)
        self.assertIn(reverse("teams:season_list"), html)

        # User-Chip & Avatar
        self.assertIn("Max Mustermann", html)
        self.assertIn("MA", html)  # Initiale aus get_short_name ("Max" -> "MA")
        self.assertIn("admin", html)

        # Admin-Links im Dropdown
        self.assertIn(reverse("admin:index"), html)
        self.assertIn("Django Admin", html)

    def test_topbar_elemente_fuer_mitglied(self):
        """Mitglied sieht 'Vereinsleben' und hat keine administrativen Menüpunkte."""
        self.client.force_login(self.mitglied)
        res = self.client.get(reverse("core:dashboard"))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode("utf-8")

        # Breadcrumb für Mitglied
        self.assertIn('>Vereinsleben<', html)
        self.assertNotIn('>Vereinsverwaltung<', html)

        # Saison-Badge als reiner Indikator (kein Admin-Link zur Saisonverwaltung)
        self.assertIn("2026/27", html)

        # Negativtest: Mitglied darf keinen Django-Admin-Link in der Topbar haben
        self.assertNotIn(reverse("admin:index"), html)
        self.assertNotIn("Django Admin", html)
        # Negativtest: Mitglied darf keine Saisonverwaltung im Dropdown haben
        self.assertNotIn(reverse("teams:season_list"), html)

    def test_topbar_ohne_begruessung_aber_dashboard_mit_hallo(self):
        """Topbar-Breadcrumbs bleiben sachlich; persönliche Begrüßung (Hallo firstname) ist im Dashboard-Inhalt."""
        # Admin Dashboard
        self.client.force_login(self.admin)
        res_admin = self.client.get(reverse("core:dashboard"))
        html_admin = res_admin.content.decode("utf-8")
        breadcrumb_match = re.search(r'<nav[^>]*class="[^"]*topbar-breadcrumb[^"]*"[^>]*>(.*?)</nav>', html_admin, re.S)
        self.assertTrue(breadcrumb_match)
        breadcrumb_html = breadcrumb_match.group(1)
        self.assertIn('>Dashboard<', breadcrumb_html)
        self.assertNotIn('Hallo', breadcrumb_html)
        self.assertNotIn('Guten Tag', breadcrumb_html)
        self.assertIn('<h1>Hallo Max.</h1>', html_admin)

        # Mitglied Dashboard (Mein Bereich)
        self.client.force_login(self.mitglied)
        res_mitglied = self.client.get(reverse("core:dashboard"))
        html_mitglied = res_mitglied.content.decode("utf-8")
        breadcrumb_match_m = re.search(r'<nav[^>]*class="[^"]*topbar-breadcrumb[^"]*"[^>]*>(.*?)</nav>', html_mitglied, re.S)
        self.assertTrue(breadcrumb_match_m)
        breadcrumb_html_m = breadcrumb_match_m.group(1)
        self.assertIn('>Mein Bereich<', breadcrumb_html_m)
        self.assertNotIn('Hallo', breadcrumb_html_m)
        self.assertNotIn('Guten Tag', breadcrumb_html_m)
        self.assertIn('<h1>Hallo Max.</h1>', html_mitglied)

    def test_negativ_kapitaen_ohne_admin_rechte_sieht_keinen_django_admin(self):
        """Negativtest: Mannschaftskapitän sieht keinen Django-Admin-Link im Dropdown."""
        self.client.force_login(self.kapitaen)
        res = self.client.get(reverse("core:dashboard"))
        html = res.content.decode("utf-8")
        self.assertNotIn(reverse("admin:index"), html)

    def test_homepage_schnelllink_reagiert_auf_module_toggle(self):
        """Öffentlicher Schnelllink wird nur gerendert, wenn Homepage-Modul aktiv ist."""
        self.client.force_login(self.admin)

        # Fall 1: Homepage aktiv
        settings_obj = ModuleSettings.get_solo()
        settings_obj.homepage_aktiv = True
        settings_obj.save()

        res = self.client.get(reverse("core:dashboard"))
        html = res.content.decode("utf-8")
        self.assertIn('class="topbar-quick-link"', html)
        self.assertIn(reverse("core:home"), html)

        # Fall 2: Negativtest - Homepage deaktiviert
        settings_obj.homepage_aktiv = False
        settings_obj.save()

        res2 = self.client.get(reverse("core:dashboard"))
        html2 = res2.content.decode("utf-8")
        self.assertNotIn('class="topbar-quick-link"', html2)

    def test_mobile_menue_schaltflaeche_hat_aria_attribute(self):
        """Der Burger-Button erfüllt Barrierefreiheitsanforderungen."""
        self.client.force_login(self.admin)
        res = self.client.get(reverse("core:dashboard"))
        html = res.content.decode("utf-8")

        self.assertIn('data-sidebar-toggle', html)
        self.assertIn('aria-controls="sidebar"', html)
        self.assertIn('aria-expanded="false"', html)
        self.assertIn('aria-label="Navigation öffnen"', html)

    def test_logout_ist_post_mit_csrf(self):
        """Abmelde-Aktion ist ein sicheres POST-Formular mit CSRF-Token."""
        self.client.force_login(self.admin)
        res = self.client.get(reverse("core:dashboard"))
        html = res.content.decode("utf-8")

        self.assertIn(f'action="{reverse("core:logout")}"', html)
        self.assertIn('csrfmiddlewaretoken', html)

    def test_topbar_css_klassen_in_app_css_definiert(self):
        """Alle neuen CSS-Klassen der Topbar sind in static/css/app.css definiert."""
        css = (settings.BASE_DIR / "static/css/app.css").read_text(encoding="utf-8")
        css_classes = set(re.findall(r"\.([a-zA-Z0-9_-]+)", css))

        erwartete_klassen = [
            "topbar",
            "topbar-left",
            "topbar-right",
            "topbar-breadcrumb",
            "breadcrumb-root",
            "breadcrumb-sep",
            "breadcrumb-current",
            "topbar-search",
            "topbar-season-badge",
            "topbar-quick-link",
            "topbar-avatar-btn",
            "topbar-dropdown",
            "topbar-dropdown-panel",
            "dropdown-header",
            "dropdown-header-info",
            "user-role-pill",
            "user-role-label",
            "mobile-menu",
        ]
        for klasse in erwartete_klassen:
            self.assertIn(
                klasse,
                css_classes,
                f"Klasse '{klasse}' fehlt in static/css/app.css",
            )
