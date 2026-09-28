from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from dues.models import FeeAmount, FeeCategory
from members.models import Member


def make_member(**kwargs):
    defaults = {
        "vorname": "Anna",
        "nachname": "Meier",
        "eintrittsdatum": date(2020, 1, 15),
    }
    defaults.update(kwargs)
    return Member.objects.create(**defaults)


class SeedTests(TestCase):
    """Die Migration 0002 legt 4 Kategorien × 2 Jahre an (PRD M2.1)."""

    def test_seed_legt_vier_kategorien_an(self):
        self.assertEqual(FeeCategory.objects.count(), 4)
        self.assertEqual(
            set(FeeCategory.objects.values_list("code", flat=True)),
            {"erwachsene", "jugend", "familie", "ermaeßigt"},
        )

    def test_seed_legt_fuer_2026_und_2027_einen_satz_an(self):
        for kategorie in FeeCategory.objects.all():
            jahre = set(
                kategorie.betraege.values_list("jahr", flat=True)
            )
            self.assertEqual(jahre, {2026, 2027}, f"{kategorie.code}: {jahre}")

    def test_acht_betraege_insgesamt(self):
        self.assertEqual(FeeAmount.objects.count(), 8)


class BetragJahreswechselTests(TestCase):
    def test_betrag_2027_aendert_2026_nicht(self):
        """Der Kern von M2.1: getrennte Sätze pro Jahr statt Überschreiben."""
        erwachsene = FeeCategory.objects.get(code="erwachsene")
        vorher = erwachsene.betraege.get(jahr=2026).betrag

        betrag_2027 = erwachsene.betraege.get(jahr=2027)
        betrag_2027.betrag = Decimal("95.50")
        betrag_2027.save()

        self.assertEqual(
            erwachsene.betraege.get(jahr=2026).betrag,
            vorher,
        )
        self.assertEqual(erwachsene.betraege.get(jahr=2027).betrag, Decimal("95.50"))


class FeeAmountValidierungTests(TestCase):
    def setUp(self):
        self.kategorie = FeeCategory.objects.get(code="erwachsene")

    def test_negativer_betrag_wird_abgelehnt(self):
        """Negativtest laut Plan T7."""
        betrag = FeeAmount(kategorie=self.kategorie, jahr=2030, betrag=Decimal("-1.00"))
        with self.assertRaises(ValidationError) as ctx:
            betrag.full_clean()
        self.assertIn("betrag", ctx.exception.message_dict)

    def test_null_betrag_wird_abgelehnt(self):
        betrag = FeeAmount(kategorie=self.kategorie, jahr=2030, betrag=None)
        with self.assertRaises(ValidationError):
            betrag.full_clean()

    def test_gueltiger_betrag_wird_akzeptiert(self):
        betrag = FeeAmount(kategorie=self.kategorie, jahr=2030, betrag=Decimal("0.00"))
        betrag.full_clean()

    def test_doppelter_satz_fuer_gleiches_jahr_wird_abgelehnt(self):
        FeeAmount.objects.create(
            kategorie=self.kategorie, jahr=2030, betrag=Decimal("80.00")
        )
        doppelt = FeeAmount(kategorie=self.kategorie, jahr=2030, betrag=Decimal("81.00"))
        with self.assertRaises(ValidationError):
            doppelt.full_clean()

    def test_doppelter_satz_wird_auch_von_der_datenbank_verhindert(self):
        FeeAmount.objects.create(
            kategorie=self.kategorie, jahr=2030, betrag=Decimal("80.00")
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FeeAmount.objects.create(
                    kategorie=self.kategorie, jahr=2030, betrag=Decimal("81.00")
                )

    def test_gleicher_satz_in_anderem_jahr_ist_erlaubt(self):
        FeeAmount.objects.create(
            kategorie=self.kategorie, jahr=2030, betrag=Decimal("80.00")
        )
        FeeAmount.objects.create(
            kategorie=self.kategorie, jahr=2031, betrag=Decimal("80.00")
        )
        self.assertEqual(self.kategorie.betraege.filter(jahr__in=[2030, 2031]).count(), 2)


class MemberKategorieTests(TestCase):
    def setUp(self):
        self.kategorie = FeeCategory.objects.get(code="jugend")

    def test_mitglied_ohne_kategorie_hat_none(self):
        """Vorbedingung für T8: ohne Kategorie wird übersprungen, nicht 0 € gebucht."""
        member = make_member()
        self.assertIsNone(member.beitragskategorie)

    def test_kategorie_zuordnung_wird_gespeichert(self):
        member = make_member(beitragskategorie=self.kategorie)
        member.refresh_from_db()
        self.assertEqual(member.beitragskategorie, self.kategorie)

    def test_ausgetretenes_mitglied_darf_keine_kategorie_haben(self):
        """Negativtest laut Plan T7."""
        member = make_member(beitragskategorie=self.kategorie)
        member.status = Member.Status.AUSGETRETEN
        member.austrittsdatum = date(2026, 6, 30)
        with self.assertRaises(ValidationError) as ctx:
            member.full_clean()
        self.assertIn("beitragskategorie", ctx.exception.message_dict)

    def test_aktives_mitglied_darf_kategorie_haben(self):
        member = make_member(beitragskategorie=self.kategorie)
        member.full_clean()

    def test_kategorie_kann_nicht_geloescht_werden_wenn_zugewiesen(self):
        member = make_member(beitragskategorie=self.kategorie)
        with self.assertRaises(ProtectedError):
            self.kategorie.delete()
        self.assertTrue(Member.objects.filter(pk=member.pk).exists())
