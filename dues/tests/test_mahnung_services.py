"""Stufenregel des Mahnwesens (PRD M2.5) — ohne HTTP, nur Services."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import AuditLog
from dues.mahnung import mahnungen_setzen, mahnstufe_text, naechste_stufe
from dues.models import FeeCategory, FeePost, Mahnung, Payment
from members.models import Member


def make_member(nachname="Meier", vorname="Anna", kategorie=None):
    return Member.objects.create(
        vorname=vorname,
        nachname=nachname,
        eintrittsdatum=date(2020, 1, 15),
        beitragskategorie=kategorie,
    )


def make_post(member=None, jahr=2026, betrag="90.00", kategorie=None):
    # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create holt
    # ihn im Testlauf, statt am unique-Slug zu scheitern.
    kategorie = kategorie or FeeCategory.objects.get_or_create(
        code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
    )[0]
    member = member or make_member(kategorie=kategorie)
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie, betrag=Decimal(betrag)
    )


def zahle(post, betrag="90.00"):
    return Payment.objects.create(
        post=post, betrag=Decimal(betrag), art=Payment.Art.BAR
    )


class MahnstufeTextTests(TestCase):
    def test_erste_und_zweite_stufe(self):
        self.assertEqual(mahnstufe_text(1), "1. Mahnung")
        self.assertEqual(mahnstufe_text(2), "2. Mahnung")

    def test_ausgeschoepfte_stufen(self):
        self.assertEqual(mahnstufe_text(None), "ausgeschöpft")


class NaechsteStufeTests(TestCase):
    def setUp(self):
        self.post = make_post()

    def test_ohne_mahnung_ist_stufe_eins_naechste(self):
        self.assertEqual(naechste_stufe(self.post), 1)

    def test_nach_erster_mahnung_ist_stufe_zwei_naechste(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        self.assertEqual(naechste_stufe(self.post), 2)

    def test_nach_zwei_mahnungen_ist_keine_stufe_mehr_frei(self):
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertIsNone(naechste_stufe(self.post))

    def test_stufe_ist_pro_posten_eigenstaendig(self):
        anderer = make_post(member=make_member(nachname="Koch", kategorie=self.post.kategorie))
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_2)

        self.assertEqual(naechste_stufe(anderer), 1)


class MahnungenSetzenTests(TestCase):
    def setUp(self):
        self.post = make_post()

    def test_setzt_die_erste_mahnung_mit_datum(self):
        mahnung = mahnungen_setzen(
            self.post, 1, date(2026, 3, 1), benutzer=User.objects.create_user("v")
        )

        self.assertEqual(mahnung.post, self.post)
        self.assertEqual(mahnung.stufe, 1)
        self.assertEqual(mahnung.datum, date(2026, 3, 1))
        self.assertIsNone(mahnung.frist)
        self.assertEqual(mahnung.notiz, "")

    def test_setzt_die_zweite_mahnung_mit_frist_und_notiz(self):
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        mahnung = mahnungen_setzen(
            self.post,
            2,
            date(2026, 4, 1),
            frist=date(2026, 4, 15),
            notiz="Telefonisch angekündigt",
        )

        self.assertEqual(mahnung.stufe, 2)
        self.assertEqual(mahnung.frist, date(2026, 4, 15))
        self.assertEqual(mahnung.notiz, "Telefonisch angekündigt")

    def test_rueckdatiertes_datum_wird_akzeptiert(self):
        """Eine Rückdatierung ist legitim — der Vorstand plant im Voraus."""

        mahnung = mahnungen_setzen(self.post, 1, date(2026, 1, 5))

        self.assertEqual(mahnung.datum, date(2026, 1, 5))

    def test_bezahlter_posten_wird_abgelehnt(self):
        zahle(self.post)

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertIn("bezahlt", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_gutschrift_wird_abgelehnt(self):
        zahle(self.post, "100.00")

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertIn("bezahlt", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_teilzahlung_bleibt_mahnbar(self):
        zahle(self.post, "40.00")

        mahnung = mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        self.assertEqual(mahnung.stufe, 1)

    def test_ueberspringen_der_stufe_wird_abgelehnt(self):
        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 2, date(2026, 3, 1))

        self.assertIn("1. Mahnung", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_doppelte_stufe_wird_abgelehnt(self):
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 4, 1))

        self.assertIn("existiert bereits", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 1)

    def test_nach_zwei_mahnungen_ist_keine_stufe_mehr_setzbar(self):
        mahnungen_setzen(self.post, 1, date(2026, 3, 1))
        mahnungen_setzen(self.post, 2, date(2026, 4, 1))

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 5, 1))

        self.assertIn("ausgeschöpft", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 2)

    def test_unbekannte_stufe_wird_abgelehnt(self):
        with self.assertRaises(ValidationError):
            mahnungen_setzen(self.post, 3, date(2026, 3, 1))

        self.assertEqual(Mahnung.objects.count(), 0)

    def test_ohne_datum_wird_abgelehnt(self):
        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, None)

        self.assertIn("Mahndatum", str(fehler.exception))
        self.assertEqual(Mahnung.objects.count(), 0)

    def test_schreibt_einen_audit_eintrag_mit_mitglied(self):
        benutzer = User.objects.create_user("vorstand")

        mahnungen_setzen(
            self.post, 1, date(2026, 3, 1), frist=date(2026, 4, 1), benutzer=benutzer
        )

        eintrag = AuditLog.objects.get(aktion="Mahnung gesetzt")
        self.assertEqual(eintrag.member, self.post.member)
        self.assertEqual(eintrag.benutzer, benutzer)
        self.assertIn("1. Mahnung", eintrag.text)
        self.assertIn("2026-03-01", eintrag.text)

    def test_doppelbuchung_aus_dem_doppelklick_ergibt_keinen_500(self):
        """Zwei gleichzeitige Klicks: die Constraint wird als ValidationError gefangen."""
        Mahnung.objects.create(post=self.post, stufe=Mahnung.Stufe.MAHNUNG_1)

        with self.assertRaises(ValidationError) as fehler:
            mahnungen_setzen(self.post, 1, date(2026, 4, 1))

        self.assertIn("existiert bereits", str(fehler.exception))
