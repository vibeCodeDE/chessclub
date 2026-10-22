"""Tests für Saisonverwaltung, Rollenberechtigungen und Negativtests (004-saison-verwaltung)."""

from datetime import date

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog
from teams.models import Season
from teams.services import create_season, set_active_season


def make_user(username, gruppe):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name=gruppe)
    user.groups.add(group)
    return user


class SeasonModelAndServiceTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin_user", "admin")
        self.saison1, _ = Season.objects.get_or_create(
            name="2025/2026",
            defaults={
                "startdatum": date(2025, 8, 1),
                "enddatum": date(2026, 7, 31),
                "status": Season.Status.AKTIV,
                "ist_aktiv": True,
            },
        )

    def test_season_erstellung_und_slug(self):
        saison = create_season(
            name="2026/2027",
            startdatum=date(2026, 8, 1),
            enddatum=date(2027, 7, 31),
            notizen="Kommende Spielzeit",
            user=self.admin,
        )
        self.assertEqual(saison.slug, "2026-2027")
        self.assertEqual(saison.status, Season.Status.VORBEREITUNG)
        self.assertFalse(saison.ist_aktiv)

        # AuditLog geprüft
        log = AuditLog.objects.filter(aktion="Saison angelegt").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.neu_wert, "2026/2027")

    def test_negativtest_ungueltiges_datum_wirft_validation_error(self):
        saison = Season(
            name="2027/2028",
            startdatum=date(2027, 8, 1),
            enddatum=date(2027, 7, 31),  # Ende vor Start!
        )
        with self.assertRaises(ValidationError) as cm:
            saison.clean()
        self.assertIn("enddatum", cm.exception.message_dict)

    def test_set_active_season_schaltet_atomar_um(self):
        saison2 = create_season(
            name="2026/2027",
            startdatum=date(2026, 8, 1),
            enddatum=date(2027, 7, 31),
            user=self.admin,
        )
        set_active_season(saison2, user=self.admin)

        saison2.refresh_from_db()
        self.saison1.refresh_from_db()

        self.assertTrue(saison2.ist_aktiv)
        self.assertEqual(saison2.status, Season.Status.AKTIV)
        self.assertFalse(self.saison1.ist_aktiv)

        # AuditLog geprüft
        log = AuditLog.objects.filter(aktion="Saison aktiviert").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.neu_wert, "2026/2027")

    def test_get_aktive_saison_fallback(self):
        Season.objects.all().update(ist_aktiv=False)
        aktive = Season.get_aktive_saison()
        self.assertEqual(aktive.pk, self.saison1.pk)


class SeasonViewRollenTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand_user", "admin")
        self.kapitaen = make_user("kapitaen_user", "kapitaen")
        self.mitglied = make_user("mitglied_user", "mitglied")
        self.saison, _ = Season.objects.get_or_create(
            name="2025/2026",
            defaults={
                "startdatum": date(2025, 8, 1),
                "enddatum": date(2026, 7, 31),
                "status": Season.Status.AKTIV,
                "ist_aktiv": True,
            },
        )

    def test_admin_kann_saison_liste_sehen(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("teams:season_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2025/2026")

    def test_negativ_kapitaen_erhaelt_403_fuer_saison_verwaltung(self):
        self.client.force_login(self.kapitaen)
        response = self.client.get(reverse("teams:season_list"))
        self.assertEqual(response.status_code, 403)

    def test_negativ_mitglied_erhaelt_403_fuer_saison_verwaltung(self):
        self.client.force_login(self.mitglied)
        response = self.client.get(reverse("teams:season_list"))
        self.assertEqual(response.status_code, 403)

    def test_negativ_gast_wird_auf_login_weitergeleitet(self):
        response = self.client.get(reverse("teams:season_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_admin_kann_saison_erstellen(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("teams:season_create"),
            {
                "name": "2026/2027",
                "startdatum": "2026-08-01",
                "enddatum": "2027-07-31",
                "status": "vorbereitung",
                "notizen": "Geplante Saison",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Season.objects.filter(name="2026/2027").exists())

    def test_admin_kann_saison_aktivieren_per_post(self):
        saison2 = Season.objects.create(
            name="2026/2027",
            startdatum=date(2026, 8, 1),
            enddatum=date(2027, 7, 31),
            status=Season.Status.VORBEREITUNG,
        )
        self.client.force_login(self.admin)
        response = self.client.post(reverse("teams:season_activate", kwargs={"pk": saison2.pk}))
        self.assertEqual(response.status_code, 302)

        saison2.refresh_from_db()
        self.assertTrue(saison2.ist_aktiv)
        self.assertEqual(saison2.status, Season.Status.AKTIV)

    def test_negativ_nicht_admin_kann_saison_nicht_aktivieren(self):
        saison2 = Season.objects.create(
            name="2026/2027",
            startdatum=date(2026, 8, 1),
            enddatum=date(2027, 7, 31),
        )
        self.client.force_login(self.kapitaen)
        response = self.client.post(reverse("teams:season_activate", kwargs={"pk": saison2.pk}))
        self.assertEqual(response.status_code, 403)

    def test_saison_liste_query_budget(self):
        from core.services import get_module_settings

        get_module_settings()
        self.client.force_login(self.admin)
        with self.assertNumQueries(13):  # Feste Obergrenze ohne N+1 (Navigation + 1 Query für Saisons mit Annotations)
            response = self.client.get(reverse("teams:season_list"))
            self.assertEqual(response.status_code, 200)
