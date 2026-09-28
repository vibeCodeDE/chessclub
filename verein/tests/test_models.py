"""Vereinsdaten: genau ein Datensatz für Brief und spätere E-Mail (T10)."""

from django.db import IntegrityError, transaction
from django.test import TestCase

from verein.models import Vereinsdaten


class VereinsdatenTests(TestCase):
    def test_aktuell_legt_den_einzigen_datensatz_an(self):
        self.assertEqual(Vereinsdaten.objects.count(), 0)

        datensatz = Vereinsdaten.aktuell()

        self.assertEqual(Vereinsdaten.objects.count(), 1)
        self.assertEqual(datensatz.pk, 1)
        self.assertEqual(datensatz.name, "Schachverein")

    def test_aktuell_liefert_beim_zweiten_mal_denselben_datensatz(self):
        erster = Vereinsdaten.aktuell()

        zweiter = Vereinsdaten.aktuell()

        self.assertEqual(erster.pk, zweiter.pk)
        self.assertEqual(Vereinsdaten.objects.count(), 1)

    def test_der_name_ist_pflicht(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as fehler:
            Vereinsdaten(name="").full_clean()

        # An das konkrete Feld binden: eine Verletzung an irgendeinem anderen
        # Feld ließe diesen Test aus dem falschen Grund grün werden.
        self.assertIn("name", fehler.exception.message_dict)

    def test_save_erzwingt_pk_eins(self):
        zweiter = Vereinsdaten.objects.create(name="Zweiter Versuch")

        self.assertEqual(zweiter.pk, 1)
        self.assertEqual(Vereinsdaten.objects.count(), 1)
        self.assertEqual(Vereinsdaten.objects.get(pk=1).name, "Zweiter Versuch")

    def test_save_ueberschreibt_den_einzigen_datensatz_still(self):
        # Der gefährliche Pfad: save() setzt pk=1, aber ein frisch
        # konstruierter Datensatz hat keine force_insert — statt zu scheitern
        # überschreibt er den bestehenden Satz. Dieser Test hält fest, dass der
        # Anlegeweg über save() (statt aktuell()) nicht vorgesehen ist.
        Vereinsdaten.objects.create(name="Erster Versuch")

        Vereinsdaten(name="Zweiter Versuch").save()

        self.assertEqual(Vereinsdaten.objects.count(), 1)
        self.assertEqual(Vereinsdaten.objects.get(pk=1).name, "Zweiter Versuch")

    def test_create_auf_belegtem_pk_bricht_laut_ab(self):
        Vereinsdaten.objects.create(name="Erster Versuch")

        with self.assertRaises(IntegrityError):
            # atomic(): der IntegrityError macht die TestCase-Transaktion
            # unbrauchbar, sonst schlägt jede folgende Abfrage fehl.
            with transaction.atomic():
                Vereinsdaten.objects.create(name="Zweiter Versuch")

        self.assertEqual(Vereinsdaten.objects.count(), 1)
        self.assertEqual(Vereinsdaten.objects.get(pk=1).name, "Erster Versuch")

    def test_str_ist_der_name(self):
        datensatz = Vereinsdaten.objects.create(name="Schachverein Example")

        self.assertEqual(str(datensatz), "Schachverein Example")

    def test_alle_felder_koennen_befuellt_werden(self):
        datensatz = Vereinsdaten.objects.create(
            name="Schachverein Example",
            strasse="Turnierweg 3",
            plz="12345",
            ort="Musterstadt",
            telefon="0123 456",
            email="kasse@example.org",
            kassierer="R. Kaiser",
            zahlungshinweis="Bitte per Überweisung ausgleichen.",
            zahlungsziel="Verwendungszweck: Nachname, Vorname, Jahr",
        )

        self.assertEqual(datensatz.ort, "Musterstadt")
        self.assertEqual(datensatz.kassierer, "R. Kaiser")
        self.assertIn("Überweisung", datensatz.zahlungshinweis)
