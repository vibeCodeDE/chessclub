"""Mahnung als Finanznachweis am Beitragsposten (PRD M2.5)."""

from datetime import date
from decimal import Decimal

from django.db.utils import IntegrityError
from django.test import TestCase

from dues.models import FeeCategory, FeePost, Mahnung
from members.models import Member


def make_post(jahr=2026, betrag="90.00"):
    # Die Kategorie stammt aus der Seed-Migration 0002 — sie wird hier nur
    # geholt, nicht neu angelegt, sonst kollidiert der Slug-Code.
    kategorie = FeeCategory.objects.get(code="erwachsene")
    member = Member.objects.create(
        vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 15),
        beitragskategorie=kategorie,
    )
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie, betrag=Decimal(betrag)
    )


class MahnungModelTests(TestCase):
    def setUp(self):
        self.post = make_post()

    def test_stufen_choices(self):
        self.assertEqual(Mahnung.Stufe.MAHNUNG_1, 1)
        self.assertEqual(Mahnung.Stufe.MAHNUNG_2, 2)
        self.assertEqual(
            [wert for wert, _ in Mahnung.Stufe.choices], [1, 2]
        )

    def test_defaults(self):
        mahnung = Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        self.assertEqual(mahnung.datum, date.today())
        self.assertIsNone(mahnung.frist)
        self.assertEqual(mahnung.notiz, "")
        self.assertIsNotNone(mahnung.erstellt)

    def test_gleiche_stufe_auf_demselben_posten_ist_unmoeglich(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        with self.assertRaises(IntegrityError):
            Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

    def test_hohere_stufe_auf_demselben_posten_ist_moeglich(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertEqual(self.post.mahnungen.count(), 2)

    def test_posten_sind_ueber_mahnungen_erreichbar(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        self.assertEqual(list(self.post.mahnungen.all())[0].stufe, 1)

    def test_posten_mit_mahnung_kann_nicht_geloescht_werden(self):
        from django.db.models import ProtectedError

        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        with self.assertRaises(ProtectedError):
            self.post.delete()

    def test_ordering_ist_neuestes_datum_zuerst(self):
        Mahnung.objects.create(
            post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1, datum=date(2026, 1, 10)
        )
        Mahnung.objects.create(
            post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2, datum=date(2026, 2, 10)
        )

        mahnungen = list(Mahnung.objects.all())

        self.assertEqual(mahnungen[0].datum, date(2026, 2, 10))
        self.assertEqual(mahnungen[1].datum, date(2026, 1, 10))

    def test_str_nennt_die_stufe_und_den_posten(self):
        mahnung = Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertIn("2. Mahnung", str(mahnung))
        # `Member.__str__` liefert "Nachname, Vorname" (siehe members/tests),
        # die Reihenfolge im Plan war hier verkehrt herum notiert.
        self.assertIn("Meier, Anna", str(mahnung))
