"""CSV-Export der Jahresbeiträge: Finanzdaten, keine Kontaktdaten (PRD M2.5)."""

import csv
import io
from datetime import date
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from dues.export import CSV_SPALTEN, beitragszeilen
from dues.mahnung import mahnungen_setzen
from dues.models import FeeCategory, FeePost, Mahnung, Payment
from members.models import Member

VERBOTENE_INHALTE = ("Musterweg", "12345", "Musterstadt", "kasse@example.org",
                     "0123 456", "1985-04-01")


def csv_zeilen(text):
    return list(csv.reader(io.StringIO(text.lstrip("\ufeff")), delimiter=";"))


def make_member(nachname="Meier", vorname="Anna", **kwargs):
    daten = {
        "vorname": vorname,
        "nachname": nachname,
        "eintrittsdatum": date(2020, 1, 15),
        "geburtsdatum": date(1985, 4, 1),
        "strasse": "Musterweg 3",
        "plz": "12345",
        "ort": "Musterstadt",
        "email": "kasse@example.org",
        "telefon": "0123 456",
    }
    daten.update(kwargs)
    return Member.objects.create(**daten)


def make_post(member, jahr=2026, betrag="90.00", kategorie=None):
    # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create holt
    # ihn im Testlauf, statt am unique-Slug zu scheitern.
    kategorie = kategorie or FeeCategory.objects.get_or_create(
        code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
    )[0]
    return FeePost.objects.create(
        member=member, jahr=jahr, kategorie=kategorie, betrag=Decimal(betrag)
    )


class CsvSpaltenTests(TestCase):
    def test_spaltenliste_ist_dokumentiert(self):
        self.assertEqual(
            CSV_SPALTEN,
            (
                "Jahr", "Nachname", "Vorname", "Kategorie", "Beitrag", "Bezahlt",
                "Offen", "Status", "Mahnungen", "1. Mahnung am", "2. Mahnung am",
            ),
        )

    def test_spaltenliste_ist_der_kopf(self):
        member = make_member()
        make_post(member)

        zeilen = beitragszeilen(2026)

        self.assertEqual(tuple(zeilen[0]), CSV_SPALTEN)


class CsvInhaltTests(TestCase):
    def setUp(self):
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

    def test_zeile_eines_unbezahlten_postens(self):
        member = make_member()
        make_post(member, kategorie=self.kategorie)

        (kopf, zeile) = beitragszeilen(2026)

        zeilenwert = dict(zip(kopf, zeile))
        self.assertEqual(zeilenwert["Jahr"], "2026")
        self.assertEqual(zeilenwert["Nachname"], "Meier")
        self.assertEqual(zeilenwert["Vorname"], "Anna")
        self.assertEqual(zeilenwert["Kategorie"], "Erwachsene")
        self.assertEqual(zeilenwert["Beitrag"], "90,00")
        self.assertEqual(zeilenwert["Bezahlt"], "0,00")
        self.assertEqual(zeilenwert["Offen"], "90,00")
        self.assertEqual(zeilenwert["Status"], "Unbezahlt")
        self.assertEqual(zeilenwert["Mahnungen"], "0")
        self.assertEqual(zeilenwert["1. Mahnung am"], "")
        self.assertEqual(zeilenwert["2. Mahnung am"], "")

    def test_zeile_eines_bezahlten_postens(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        Payment.objects.create(
            post=post, betrag=Decimal("90.00"), art=Payment.Art.BAR
        )

        (kopf, zeile) = beitragszeilen(2026)

        zeilenwert = dict(zip(kopf, zeile))
        self.assertEqual(zeilenwert["Bezahlt"], "90,00")
        self.assertEqual(zeilenwert["Offen"], "0,00")
        self.assertEqual(zeilenwert["Status"], "Bezahlt")

    def test_mahndaten_stehen_in_ihren_spalten(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        mahnungen_setzen(post, 1, date(2026, 3, 1))
        mahnungen_setzen(post, 2, date(2026, 4, 15))

        (kopf, zeile) = beitragszeilen(2026)

        zeilenwert = dict(zip(kopf, zeile))
        self.assertEqual(zeilenwert["Mahnungen"], "2")
        self.assertEqual(zeilenwert["1. Mahnung am"], "2026-03-01")
        self.assertEqual(zeilenwert["2. Mahnung am"], "2026-04-15")

    def test_mahnungen_werden_als_iso_datum_ausgegeben(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        mahnungen_setzen(post, 1, date(2026, 3, 1), frist=date(2026, 4, 1))

        (kopf, zeile) = beitragszeilen(2026)

        zeilenwert = dict(zip(kopf, zeile))
        # Die Frist steht bewusst nicht in der Datei — sie gehört in den Brief.
        self.assertEqual(zeilenwert["1. Mahnung am"], "2026-03-01")

    def test_alle_posten_des_jahres(self):
        for nummer in range(4):
            make_post(
                make_member(nachname=f"Mustermann{nummer:02d}"),
                kategorie=self.kategorie,
            )
        make_post(make_member(nachname="Später"), jahr=2027, kategorie=self.kategorie)

        zeilen = beitragszeilen(2026)

        self.assertEqual(len(zeilen) - 1, 4)
        self.assertEqual(FeePost.objects.filter(jahr=2026).count(), 4)

    def test_bezahlte_posten_sind_enthalten(self):
        """Der Export ist die Jahresübersicht, nicht die Mahnliste."""
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        Payment.objects.create(
            post=post, betrag=Decimal("90.00"), art=Payment.Art.BAR
        )

        zeilen = beitragszeilen(2026)

        self.assertEqual(len(zeilen) - 1, 1)

    def test_leeres_jahr_liefert_nur_den_kopf(self):
        self.assertEqual(beitragszeilen(2026), [list(CSV_SPALTEN)])

    def test_sortiert_nach_nachname_und_vorname(self):
        make_post(make_member(nachname="Ziegler"), kategorie=self.kategorie)
        make_post(make_member(nachname="Bauer"), kategorie=self.kategorie)
        make_post(make_member(nachname="Aigner"), kategorie=self.kategorie)

        zeilen = beitragszeilen(2026)

        nachnamen = [zeile[1] for zeile in zeilen[1:]]
        self.assertEqual(nachnamen, ["Aigner", "Bauer", "Ziegler"])

    def test_zwei_exporte_sind_identisch(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        mahnungen_setzen(post, 1, date(2026, 3, 1))

        self.assertEqual(beitragszeilen(2026), beitragszeilen(2026))

    def test_jahressumme_entspricht_der_modellsumme(self):
        for nummer, betrag in enumerate(("90.00", "50.00", "45.00")):
            post = make_post(
                make_member(nachname=f"Mustermann{nummer:02d}"),
                betrag=betrag,
                kategorie=self.kategorie,
            )
            Payment.objects.create(
                post=post, betrag=Decimal("20.00"), art=Payment.Art.BAR
            )

        zeilen = beitragszeilen(2026)
        offene_spalte = CSV_SPALTEN.index("Offen")

        export_summe = sum(
            (Decimal(zeile[offene_spalte].replace(",", ".")) for zeile in zeilen[1:]),
            Decimal("0.00"),
        )
        modell_summe = sum(
            (
                post.betrag
                - sum(
                    z.betrag
                    for z in Payment.objects.filter(post=post)
                )
                for post in FeePost.objects.filter(jahr=2026)
            ),
            Decimal("0.00"),
        )

        self.assertEqual(export_summe, modell_summe)
        # 90 + 50 + 45 abzüglich 3 × 20 gezahlt = 125. Der Wert im Briefing
        # (135,00) war ein Rechenfehler; die tragende Zusicherung ist der
        # Vergleich Export gegen Modell darüber.
        self.assertEqual(export_summe, Decimal("125.00"))

    def test_keine_n_plus_eins_abfrage(self):
        """Posten+Status und Mahnungen — zwei Abfragen, unabhängig von der Menge."""
        for nummer in range(5):
            post = make_post(
                make_member(nachname=f"Mustermann{nummer:02d}"),
                kategorie=self.kategorie,
            )
            mahnungen_setzen(post, 1, date(2026, 3, 1))
        beitragszeilen(2026)  # Aufwärmen, damit keine Schemaabfrage mitzählt.

        with CaptureQueriesContext(connection) as abfragen:
            beitragszeilen(2026)

        self.assertEqual(len(abfragen), 2)


class CsvDatensparsamkeitTests(TestCase):
    """Inhaltstest aus plan.md: der Export enthält keine Kontaktdaten."""

    def setUp(self):
        # "erwachsene" wird von der Seed-Migration 0002 angelegt; get_or_create
        # holt ihn im Testlauf, statt am unique-Slug zu scheitern.
        self.kategorie = FeeCategory.objects.get_or_create(
            code="erwachsene", defaults={"bezeichnung": "Erwachsene"}
        )[0]

    def test_keine_adressen_und_keine_kontaktdaten(self):
        member = make_member()
        post = make_post(member, kategorie=self.kategorie)
        mahnungen_setzen(post, 1, date(2026, 3, 1))

        zeilen = beitragszeilen(2026)
        volltext = "\n".join(";".join(zeile) for zeile in zeilen)

        for verboten in VERBOTENE_INHALTE:
            self.assertNotIn(verboten, volltext)

    def test_keine_adressen_anderer_mitglieder(self):
        """Adressen Dritter landen nicht im Export — auch nicht über die Mahnhistorie."""
        exportiert = make_member(nachname="Exportiert")
        # Eigene Kontaktdaten, sonst könnte der Fund nicht zugeordnet werden.
        fremd = make_member(
            nachname="Fremd",
            vorname="Fritz",
            strasse="Fremdweg 9",
            plz="54321",
            ort="Fremdstadt",
            email="fritz@example.org",
            telefon="0987 654",
            geburtsdatum=date(1970, 2, 3),
        )
        make_post(exportiert, kategorie=self.kategorie)
        post_fremd = make_post(fremd, kategorie=self.kategorie)
        mahnungen_setzen(post_fremd, 1, date(2026, 3, 1))

        zeilen = beitragszeilen(2026)
        volltext = "\n".join(";".join(zeile) for zeile in zeilen)

        # Namensspalten stehen im Export, Kontaktdaten niemals — auch dann nicht,
        # wenn am Posten des dritten Mitglieds eine Mahnung hängt.
        for verboten in (
            "Fremdweg 9", "54321", "Fremdstadt", "fritz@example.org",
            "0987 654", "1970-02-03",
        ):
            self.assertNotIn(verboten, volltext)
        # Der eigene Posten des exportierten Mitglieds steht sehr wohl drin.
        self.assertIn("Exportiert", volltext)

    def test_jede_zeile_hat_so_viele_spalten_wie_der_kopf(self):
        make_post(make_member(), kategorie=self.kategorie)
        make_post(make_member(nachname="Zweiter"), kategorie=self.kategorie)

        zeilen = beitragszeilen(2026)

        for zeile in zeilen:
            self.assertEqual(len(zeile), len(CSV_SPALTEN))

    def test_zeilen_lesen_sich_als_csv(self):
        make_post(make_member(), kategorie=self.kategorie)

        zeilen = beitragszeilen(2026)
        text = "\n".join(";".join(zeile) for zeile in zeilen)

        self.assertEqual(csv_zeilen(text)[0], list(CSV_SPALTEN))
