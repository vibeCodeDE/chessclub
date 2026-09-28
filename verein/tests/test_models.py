"""Vereinsdaten: genau ein Datensatz für Brief und spätere E-Mail (T10)."""

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

        with self.assertRaises(ValidationError):
            Vereinsdaten(name="").full_clean()

    def test_save_erzwingt_pk_eins(self):
        zweiter = Vereinsdaten.objects.create(name="Zweiter Versuch")

        self.assertEqual(zweiter.pk, 1)
        self.assertEqual(Vereinsdaten.objects.count(), 1)

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
