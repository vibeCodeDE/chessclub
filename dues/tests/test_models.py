from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from dues.models import FeeAmount, FeeCategory, FeePost, Payment, SepaMandate
from members.models import Member


def make_member(**kwargs):
    defaults = {
        "vorname": "Anna",
        "nachname": "Meier",
        "eintrittsdatum": date(2020, 1, 15),
    }
    defaults.update(kwargs)
    return Member.objects.create(**defaults)


def make_post(jahr=2026, betrag="90.00"):
    """Beitragsposten für Zahlungstests — wie vom Beitragslauf erzeugt."""
    kategorie = FeeCategory.objects.get(code="erwachsene")
    member = make_member(beitragskategorie=kategorie)
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie, betrag=Decimal(betrag)
    )


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


class SepaMandateTests(TestCase):
    """SEPA-Mandate (PRD M2.3) — nur Referenz, Datum und Status, keine IBAN."""

    def setUp(self):
        self.member = make_member()

    def test_mandat_ist_standardmaessig_aktiv(self):
        mandat = SepaMandate.objects.create(member=self.member, referenz="M-2026-001")

        self.assertEqual(mandat.status, SepaMandate.Status.AKTIV)
        self.assertEqual(mandat.datum, date.today())

    def test_mandat_hat_die_drei_vereinbarten_status(self):
        self.assertEqual(
            {wert for wert, _ in SepaMandate.Status.choices},
            {"aktiv", "widerrufen", "beendet"},
        )

    def test_referenz_ist_eindeutig(self):
        """Negativtest: zwei Mandate mit derselben Referenz sind unmöglich."""
        SepaMandate.objects.create(member=self.member, referenz="M-2026-001")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SepaMandate.objects.create(member=self.member, referenz="M-2026-001")

    def test_mandat_haengt_am_mitglied(self):
        mandat = SepaMandate.objects.create(member=self.member, referenz="M-1")
        self.assertEqual(list(self.member.sepa_mandate.all()), [mandat])


class PaymentValidierungTests(TestCase):
    """Zahlungen (PRD M2.4) — von Hand gebucht, SEPA nur mit aktivem Mandat."""

    def setUp(self):
        self.post = make_post()

    def test_sepa_zahlung_ohne_mandat_wird_abgelehnt(self):
        """Negativtest laut Plan T9: SEPA braucht ein Mandat."""
        payment = Payment(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.SEPA
        )

        with self.assertRaises(ValidationError) as ctx:
            payment.full_clean()

        self.assertIn("art", ctx.exception.message_dict)

    def test_sepa_mit_widerrufenem_mandat_wird_abgelehnt(self):
        """Negativtest: ein widerrufenes Mandat trägt keinen Einzug."""
        SepaMandate.objects.create(
            member=self.post.member,
            referenz="M-1",
            status=SepaMandate.Status.WIDERRUFEN,
        )
        payment = Payment(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.SEPA
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_sepa_mit_aktivem_mandat_ist_gueltig(self):
        SepaMandate.objects.create(member=self.post.member, referenz="M-1")
        payment = Payment(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.SEPA
        )

        payment.full_clean()

    def test_ueberweisung_ohne_mandat_ist_gueltig(self):
        payment = Payment(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.UEBERWEISUNG
        )

        payment.full_clean()

    def test_barzahlung_ist_ohne_mandat_gueltig(self):
        payment = Payment(post=self.post, betrag=Decimal("10.00"), art=Payment.Art.BAR)

        payment.full_clean()

    def test_betrag_null_wird_abgelehnt(self):
        """Negativtest: eine 0-€-Buchung ist keine Buchung."""
        payment = Payment(post=self.post, betrag=Decimal("0.00"), art=Payment.Art.BAR)

        with self.assertRaises(ValidationError) as ctx:
            payment.full_clean()

        self.assertIn("betrag", ctx.exception.message_dict)

    def test_storno_verweist_auf_die_originalzahlung(self):
        SepaMandate.objects.create(member=self.post.member, referenz="M-1")
        original = Payment.objects.create(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.SEPA
        )

        storno = Payment.objects.create(
            post=self.post,
            betrag=Decimal("-90.00"),
            art=Payment.Art.SEPA,
            storno_von=original,
        )

        self.assertEqual(list(original.stornos.all()), [storno])

    def test_zahlung_ist_nicht_geloeschbar_wenn_posten_existiert(self):
        """Negativtest: die Finanzhistorie bleibt (PROTECT auf beiden Seiten)."""
        Payment.objects.create(
            post=self.post, betrag=Decimal("90.00"), art=Payment.Art.BAR
        )

        with self.assertRaises(ProtectedError):
            self.post.delete()
