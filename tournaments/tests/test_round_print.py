"""Tests für den Rundenaushang-Druck (Hebel F3 & D3)."""

from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from tournaments.models import Participant, Tournament
from tournaments.pairing import generate_round


def make_user(username, role="admin"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    return user


class RoundPrintViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("turnierleiter", "admin")
        cls.kapitaen = make_user("kapitaen_user", "kapitaen")
        cls.mitglied = make_user("mitglied_user", "mitglied")

        cls.turnier = Tournament.objects.create(
            name="Vereinsmeisterschaft 2026",
            datum=date(2026, 11, 20),
            status=Tournament.Status.LAUFEND,
            runden_anzahl=5,
            ort="Klubraum",
            oeffentlich=True,
        )

        Participant.objects.create(
            tournament=cls.turnier, name="Anton Adler", twz=2050, verein="SC Königsspringer",
        )
        Participant.objects.create(
            tournament=cls.turnier, name="Berta Bär", twz=1980, verein="SC Königsspringer",
        )
        Participant.objects.create(
            tournament=cls.turnier, name="Carl Chamäleon", twz=1820, verein="SK Turm",
        )
        Participant.objects.create(
            tournament=cls.turnier, name="Dora Drossel", twz=1750, verein="SC Königsspringer",
        )

        generate_round(cls.turnier)

    def test_round_print_admin_erfolg(self):
        self.client.force_login(self.admin)
        url = reverse("tournaments:round_print", kwargs={"pk": self.turnier.pk, "runde_nr": 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Rundenaushang", content)
        self.assertIn("Vereinsmeisterschaft 2026", content)
        self.assertIn("Runde 1", content)
        self.assertIn("Anton Adler", content)
        self.assertIn("2050", content)
        self.assertIn("Brett 1", content)

    def test_round_print_negativtest_403(self):
        # PRD §3.8: Rolle kapitaen und mitglied dürfen Turniere nicht verwalten (403)
        url = reverse("tournaments:round_print", kwargs={"pk": self.turnier.pk, "runde_nr": 1})
        for user in [self.kapitaen, self.mitglied]:
            self.client.force_login(user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, f"User {user.username} should get 403")

    def test_round_print_negativtest_gast_redirect(self):
        url = reverse("tournaments:round_print", kwargs={"pk": self.turnier.pk, "runde_nr": 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/anmelden/", response.url)

    def test_round_print_negativtest_404_fuer_ungueltige_runde(self):
        self.client.force_login(self.admin)
        url = reverse("tournaments:round_print", kwargs={"pk": self.turnier.pk, "runde_nr": 99})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
