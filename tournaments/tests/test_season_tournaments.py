"""Tests für die saisonbezogene Gliederung von Vereinsturnieren (US4)."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.roles import ADMIN_GROUP, MITGLIED_GROUP
from teams.models import Season
from teams.services import delete_season
from tournaments.forms import TournamentForm
from tournaments.models import Tournament

User = get_user_model()


class SeasonTournamentTests(TestCase):
    """Testet Zuordnung von Turnieren zu Saisons und Filterung im Turnierarchiv."""

    def setUp(self):
        admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        mitglied_group, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)

        self.admin = User.objects.create_user(username="admin_turnier", password="password123")
        self.admin.groups.add(admin_group)

        self.mitglied = User.objects.create_user(username="mitglied_turnier", password="password123")
        self.mitglied.groups.add(mitglied_group)

        self.saison_alt, _ = Season.objects.get_or_create(
            name="2024/2025",
            defaults={
                "startdatum": date(2024, 8, 1),
                "enddatum": date(2025, 7, 31),
                "status": Season.Status.ARCHIVIERT,
                "ist_aktiv": False,
            },
        )
        self.saison_neu, _ = Season.objects.get_or_create(
            name="2025/2026",
            defaults={
                "startdatum": date(2025, 8, 1),
                "enddatum": date(2026, 7, 31),
                "status": Season.Status.AKTIV,
                "ist_aktiv": True,
            },
        )
        self.saison_neu.ist_aktiv = True
        self.saison_neu.save()

        self.turnier_alt = Tournament.objects.create(
            name="Vereinsmeisterschaft 2024/2025",
            saison=self.saison_alt,
            datum=date(2024, 11, 15),
            status=Tournament.Status.BEENDET,
            oeffentlich=True,
        )
        self.turnier_neu = Tournament.objects.create(
            name="Vereinsmeisterschaft 2025/2026",
            saison=self.saison_neu,
            datum=date(2025, 11, 15),
            status=Tournament.Status.ANMELDUNG,
            oeffentlich=True,
        )
        self.turnier_offen = Tournament.objects.create(
            name="Offenes Sommerturnier (Saisonunabhängig)",
            saison=None,
            datum=date(2025, 7, 10),
            status=Tournament.Status.BEENDET,
            oeffentlich=True,
        )

    def test_turnier_kann_saison_zugeordnet_oder_unabhaengig_sein(self):
        self.assertEqual(self.turnier_alt.saison, self.saison_alt)
        self.assertEqual(self.turnier_neu.saison, self.saison_neu)
        self.assertIsNone(self.turnier_offen.saison)

    def test_tournament_form_belegt_aktive_saison_vor(self):
        form = TournamentForm()
        self.assertEqual(form.fields["saison"].initial, self.saison_neu)

    def test_manage_list_filtert_nach_saison(self):
        self.client.force_login(self.admin)
        # Filter nach Saison Alt
        res_alt = self.client.get(f"{reverse('tournaments:manage_list')}?saison={self.saison_alt.pk}")
        self.assertEqual(res_alt.status_code, 200)
        self.assertContains(res_alt, "Vereinsmeisterschaft 2024/2025")
        self.assertNotContains(res_alt, "Vereinsmeisterschaft 2025/2026")

        # Filter nach Saison Neu
        res_neu = self.client.get(f"{reverse('tournaments:manage_list')}?saison={self.saison_neu.pk}")
        self.assertEqual(res_neu.status_code, 200)
        self.assertContains(res_neu, "Vereinsmeisterschaft 2025/2026")
        self.assertNotContains(res_neu, "Vereinsmeisterschaft 2024/2025")

    def test_public_list_filtert_nach_saison(self):
        res = self.client.get(f"{reverse('tournaments:public_list')}?saison={self.saison_alt.pk}")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Vereinsmeisterschaft 2024/2025")
        self.assertNotContains(res, "Vereinsmeisterschaft 2025/2026")

    def test_negativ_loeschen_einer_saison_mit_turnieren_wird_abgewehrt(self):
        with self.assertRaises(ValidationError) as ctx:
            delete_season(self.saison_alt, user=self.admin)
        self.assertIn("zugeordnet", str(ctx.exception))
