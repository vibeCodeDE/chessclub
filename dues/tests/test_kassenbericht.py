"""Kassenbericht Beitragsverwaltung (PRD M2.6, Task T11b).

Reine Lese-Sicht auf Beitragszahlungen je Mitglied für ein gewähltes Jahr,
Jahressumme der Einnahmen und offene Posten zum Stichtag sowie CSV-Export.
"""

import csv
import io
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from dues.models import FeeAmount, FeeCategory, MembershipFee, Payment
from dues.services import beitragslauf, zahlung_erfassen, zahlung_stornieren
from members.models import Member


def make_admin(username="kassenpruefer"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


class KassenberichtTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_admin()
        cls.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=cls.kategorie, jahr=2026, betrag=Decimal("90.00"))
        cls.ermaessigt = FeeCategory.objects.create(name="Ermäßigt")
        FeeAmount.objects.create(kategorie=cls.ermaessigt, jahr=2026, betrag=Decimal("45.00"))

        # 10 Mitglieder anlegen
        cls.mitglieder = []
        for i in range(10):
            kat = cls.kategorie if i < 7 else cls.ermaessigt
            m = Member.objects.create(
                vorname=f"Vorname{i:02d}",
                nachname=f"Nachname{i:02d}",
                eintrittsdatum=date(2020, 1, 1),
                email=f"mitglied{i}@example.org",
                beitragskategorie=kat,
            )
            cls.mitglieder.append(m)

        # Beitragslauf 2026 erzeugt 10 Posten
        beitragslauf(2026)

        # 8 Mitglieder leisten Zahlungen (5 voll, 3 teilweise)
        cls.zahlungen = []
        for i in range(8):
            fee = MembershipFee.objects.get(member=cls.mitglieder[i], jahr=2026)
            betrag = fee.betrag if i < 5 else Decimal("30.00")
            z = zahlung_erfassen(
                fee,
                betrag=betrag,
                datum=date(2026, 2, 10 + i),
                art=Payment.Art.UEBERWEISUNG if i % 2 == 0 else Payment.Art.SEPA,
                notiz=f"Zahlung M{i}",
                benutzer=cls.admin,
            )
            cls.zahlungen.append(z)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_kassenbericht_10_mitglieder_8_zahlungen(self):
        """Für 10 Mitglieder und 8 Zahlungen zeigt die Übersicht genau 8 Zeilen.

        Die Jahressumme entspricht der im Test berechneten Modellsumme.
        """
        antwort = self.client.get("/beitraege/kassenbericht/?jahr=2026")
        self.assertEqual(antwort.status_code, 200)

        # Kontext prüfen
        zahlungen_im_kontext = antwort.context["zahlungen"]
        self.assertEqual(len(zahlungen_im_kontext), 8)

        # Referenzrechnung: Jahressumme gegen Modellsumme prüfen
        modell_summe = sum(
            (p.betrag for p in Payment.objects.filter(fee__jahr=2026)),
            Decimal("0.00"),
        )
        self.assertEqual(antwort.context["jahressumme"], modell_summe)

        # HTML prüfen: Alle 8 Zahlenden namentlich im Dokument
        for i in range(8):
            self.assertContains(antwort, f"Nachname{i:02d}")

        # Die 2 Nicht-Zahler erscheinen nicht in der Zahlungstabelle
        self.assertNotContains(antwort, "Zahlung M8")
        self.assertNotContains(antwort, "Zahlung M9")

        # Offene Posten: 2 voll unbezahlt + 3 teilbezahlt = 5 offene Posten
        self.assertEqual(len(antwort.context["offene_posten"]), 5)

    def test_leeres_jahr_zeigt_keine_buchungen_statt_null_euro_zeilen(self):
        """Ein Jahr ohne Daten zeigt „keine Buchungen“ statt leerer 0-€-Zeilen."""
        antwort = self.client.get("/beitraege/kassenbericht/?jahr=2024")
        self.assertEqual(antwort.status_code, 200)
        self.assertEqual(len(antwort.context["zahlungen"]), 0)
        self.assertEqual(len(antwort.context["offene_posten"]), 0)
        self.assertEqual(antwort.context["jahressumme"], Decimal("0.00"))

        # HTML enthält Hinweistext
        self.assertContains(antwort, "Keine Buchungen für das Jahr 2024 vorhanden.")

    def test_kassenbericht_csv_export_summiert_identisch_zur_anzeige(self):
        """Der CSV-Export summiert identisch zur Anzeige und Modellsumme."""
        antwort = self.client.get("/beitraege/kassenbericht/export.csv?jahr=2026")
        self.assertEqual(antwort.status_code, 200)
        self.assertEqual(antwort["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn('filename="kassenbericht-beitraege-2026.csv"', antwort["Content-Disposition"])

        text = antwort.content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text), delimiter=";")
        zeilen = list(reader)

        # Kopfzeile + 8 Datenzeilen
        self.assertEqual(zeilen[0], ["Datum", "Nachname", "Vorname", "Kategorie", "Zahlungsart", "Betrag", "Notiz"])
        self.assertEqual(len(zeilen), 9)

        # CSV-Summe parsen und mit Modellsumme abgleichen
        csv_summe = sum(
            Decimal(z[5].replace(",", ".")) for z in zeilen[1:]
        )
        modell_summe = sum(
            (p.betrag for p in Payment.objects.filter(fee__jahr=2026)),
            Decimal("0.00"),
        )
        self.assertEqual(csv_summe, modell_summe)

    def test_storno_mindert_jahressumme(self):
        """Storno-Gegenbuchung erscheint im Kassenbericht und verringert die Summe."""
        zahlung = self.zahlungen[0]
        ursprung_betrag = zahlung.betrag
        zahlung_stornieren(zahlung, grund="Rückabwicklung", benutzer=self.admin)

        antwort = self.client.get("/beitraege/kassenbericht/?jahr=2026")
        self.assertEqual(antwort.status_code, 200)

        # 8 Originalzahlungen + 1 Stornobuchung = 9 Zeilen
        self.assertEqual(len(antwort.context["zahlungen"]), 9)

        neue_modell_summe = sum(
            (p.betrag for p in Payment.objects.filter(fee__jahr=2026)),
            Decimal("0.00"),
        )
        self.assertEqual(antwort.context["jahressumme"], neue_modell_summe)
        self.assertContains(antwort, f"-{ursprung_betrag:.2f} €".replace(".", ","))

    def test_kassenbericht_export_escapes_csv_formulas(self):
        """Negativtest: Verhindert Formula Injection (CWE-1236) im Kassenbericht-Zahlungs-Export."""
        m = Member.objects.create(
            vorname="+InjectedVorname",
            nachname="=cmd|' /C calc'!A0",
            eintrittsdatum=date(2020, 1, 1),
            beitragskategorie=self.kategorie,
        )
        fee = MembershipFee.objects.create(
            member=m,
            jahr=2026,
            kategorie_name="@EvilKategorie",
            betrag=Decimal("90.00"),
            faellig_am=date(2026, 1, 31),
        )
        Payment.objects.create(
            fee=fee,
            betrag=Decimal("90.00"),
            datum=date(2026, 3, 1),
            notiz="-DDE('calc')",
        )
        antwort = self.client.get("/beitraege/kassenbericht/export.csv?jahr=2026")
        self.assertEqual(antwort.status_code, 200)
        inhalt = antwort.content.decode("utf-8-sig")
        self.assertIn("'=cmd|' /C calc'!A0", inhalt)
        self.assertIn("'+InjectedVorname", inhalt)
        self.assertIn("'@EvilKategorie", inhalt)
        self.assertIn("'-DDE('calc')", inhalt)

