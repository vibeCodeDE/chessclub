"""Tests für den SEPA-XML-Export (pain.008.001.02, PRD S2.7, ADR-017)."""

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from core.models import AuditLog
from dues.models import FeeAmount, FeeCategory, MembershipFee, Payment, SepaMandate
from dues.services import erstelle_sepa_xml, sepa_sanitize
from members.models import Member

XML_NS = "{urn:iso:std:iso:20022:tech:xsd:pain.008.001.02}"


def make_admin(username="kassenwart"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


class SepaSanitizeTests(TestCase):
    def test_deutsche_umlaute_und_sonderzeichen(self):
        text = "Müller-Lüdenscheidt & Söhne (Größe: 100%)"
        bereinigt = sepa_sanitize(text)
        self.assertEqual(bereinigt, "Mueller-Luedenscheidt + Soehne (Groesse: 100 )")

    def test_laengenbegrenzung(self):
        text = "Ein sehr langer Text der abgeschnitten werden muss"
        bereinigt = sepa_sanitize(text, max_len=15)
        self.assertEqual(bereinigt, "Ein sehr langer")
        self.assertLessEqual(len(bereinigt), 15)

    def test_leerer_text(self):
        self.assertEqual(sepa_sanitize(""), "")
        self.assertEqual(sepa_sanitize(None), "")


class SepaExportServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=cls.kategorie, jahr=2026, betrag=Decimal("90.00"))
        FeeAmount.objects.create(kategorie=cls.kategorie, jahr=2025, betrag=Decimal("80.00"))

        # Mitglied 1: Aktiv mit gültigem Mandat
        cls.m1 = Member.objects.create(
            vorname="Max", nachname="Mustermann",
            eintrittsdatum=date(2020, 1, 1), beitragskategorie=cls.kategorie,
        )
        cls.mandat1 = SepaMandate.objects.create(
            member=cls.m1, referenz="MND-001",
            iban="DE89370400440532013000", kontoinhaber="Max Mustermann",
            erteilt_am=date(2025, 1, 10), status=SepaMandate.Status.AKTIV,
        )
        cls.fee1 = MembershipFee.objects.create(
            member=cls.m1, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )

        # Mitglied 2: Aktiv mit Umlauten im Namen und Teilzahlung
        cls.m2 = Member.objects.create(
            vorname="Jürgen", nachname="Schröder",
            eintrittsdatum=date(2021, 5, 1), beitragskategorie=cls.kategorie,
        )
        cls.mandat2 = SepaMandate.objects.create(
            member=cls.m2, referenz="MND-002",
            iban="DE12500105170648489890", kontoinhaber="Jürgen Schröder",
            erteilt_am=date(2025, 2, 15), status=SepaMandate.Status.AKTIV,
        )
        cls.fee2 = MembershipFee.objects.create(
            member=cls.m2, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )
        # Teilzahlung über 30 € -> 60 € offen
        Payment.objects.create(
            fee=cls.fee2, betrag=Decimal("30.00"), art=Payment.Art.UEBERWEISUNG,
            datum=date(2026, 2, 1),
        )
        cls.fee2.status_aktualisieren()

        # Mitglied 3: Voll bezahlt -> darf nicht im Export sein
        cls.m3 = Member.objects.create(
            vorname="Bezahlt", nachname="Voll",
            eintrittsdatum=date(2022, 1, 1), beitragskategorie=cls.kategorie,
        )
        cls.mandat3 = SepaMandate.objects.create(
            member=cls.m3, referenz="MND-003",
            iban="DE22100110012345678901", kontoinhaber="Bezahlt Voll",
            erteilt_am=date(2025, 3, 1), status=SepaMandate.Status.AKTIV,
        )
        cls.fee3 = MembershipFee.objects.create(
            member=cls.m3, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )
        Payment.objects.create(
            fee=cls.fee3, betrag=Decimal("90.00"), art=Payment.Art.UEBERWEISUNG,
            datum=date(2026, 2, 1),
        )
        cls.fee3.status_aktualisieren()

        # Mitglied 4: Widerrufenes Mandat -> darf nicht im Export sein
        cls.m4 = Member.objects.create(
            vorname="Widerruf", nachname="Person",
            eintrittsdatum=date(2022, 1, 1), beitragskategorie=cls.kategorie,
        )
        SepaMandate.objects.create(
            member=cls.m4, referenz="MND-004",
            iban="DE33100110012345678902", kontoinhaber="Widerruf Person",
            erteilt_am=date(2025, 3, 1), status=SepaMandate.Status.WIDERRUFEN,
            widerrufen_am=date(2025, 6, 1),
        )
        cls.fee4 = MembershipFee.objects.create(
            member=cls.m4, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )

        # Mitglied 5: Ohne Mandat -> darf nicht im Export sein
        cls.m5 = Member.objects.create(
            vorname="Kein", nachname="Mandat",
            eintrittsdatum=date(2022, 1, 1), beitragskategorie=cls.kategorie,
        )
        cls.fee5 = MembershipFee.objects.create(
            member=cls.m5, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )

    def test_sepa_xml_erfolgreich_mit_pain008_struktur(self):
        xml_bytes, meta = erstelle_sepa_xml(2026, ausfuehrung_am=date(2026, 3, 15))

        self.assertEqual(meta["anzahl_posten"], 2)
        # fee1: 90.00 €, fee2: 60.00 € (Restbetrag nach 30 € Teilzahlung)
        self.assertEqual(meta["gesamtsumme"], Decimal("150.00"))
        self.assertEqual(meta["jahr"], 2026)

        root = ET.fromstring(xml_bytes)
        self.assertEqual(root.tag, f"{XML_NS}Document")

        cstmr = root.find(f"{XML_NS}CstmrDrctDbtInitn")
        self.assertIsNotNone(cstmr)

        # Group Header
        grp_hdr = cstmr.find(f"{XML_NS}GrpHdr")
        self.assertIsNotNone(grp_hdr)
        self.assertEqual(grp_hdr.find(f"{XML_NS}NbOfTxs").text, "2")
        self.assertEqual(grp_hdr.find(f"{XML_NS}CtrlSum").text, "150.00")
        self.assertTrue(grp_hdr.find(f"{XML_NS}MsgId").text)

        # Payment Info
        pmt_inf = cstmr.find(f"{XML_NS}PmtInf")
        self.assertIsNotNone(pmt_inf)
        self.assertEqual(pmt_inf.find(f"{XML_NS}PmtMtd").text, "DD")
        self.assertEqual(pmt_inf.find(f"{XML_NS}NbOfTxs").text, "2")
        self.assertEqual(pmt_inf.find(f"{XML_NS}CtrlSum").text, "150.00")
        self.assertEqual(pmt_inf.find(f"{XML_NS}ReqdColltnDt").text, "2026-03-15")

        # Payment Type Info
        pmt_tp_inf = pmt_inf.find(f"{XML_NS}PmtTpInf")
        self.assertEqual(pmt_tp_inf.find(f"{XML_NS}SvcLvl/{XML_NS}Cd").text, "SEPA")
        self.assertEqual(pmt_tp_inf.find(f"{XML_NS}LclInstrm/{XML_NS}Cd").text, "CORE")
        self.assertEqual(pmt_tp_inf.find(f"{XML_NS}SeqTp").text, "RCUR")

        # Creditor Scheme ID (Gläubiger-ID)
        ci_elem = pmt_inf.find(
            f"{XML_NS}CdtrSchmeId/{XML_NS}Id/{XML_NS}OrgId/{XML_NS}Othr/{XML_NS}Id"
        )
        self.assertIsNotNone(ci_elem)
        self.assertEqual(ci_elem.text, "DE98ZZZ09999999999")

        # Transactions
        tx_list = pmt_inf.findall(f"{XML_NS}DrctDbtTxInf")
        self.assertEqual(len(tx_list), 2)

        # Transaktion 1 (Max Mustermann, 90.00 €)
        tx1 = tx_list[0]
        amt1 = tx1.find(f"{XML_NS}InstdAmt")
        self.assertEqual(amt1.attrib["Ccy"], "EUR")
        self.assertEqual(amt1.text, "90.00")
        mndt1 = tx1.find(f"{XML_NS}DrctDbtTx/{XML_NS}MndtRltdInf")
        self.assertEqual(mndt1.find(f"{XML_NS}MndtId").text, "MND-001")
        self.assertEqual(mndt1.find(f"{XML_NS}DtOfSgntr").text, "2025-01-10")
        dbtr1 = tx1.find(f"{XML_NS}Dbtr/{XML_NS}Nm").text
        self.assertEqual(dbtr1, "Max Mustermann")
        iban1 = tx1.find(f"{XML_NS}DbtrAcct/{XML_NS}Id/{XML_NS}IBAN").text
        self.assertEqual(iban1, "DE89370400440532013000")

        # Transaktion 2 (Jürgen Schröder -> bereinigt Juergen Schroeder, 60.00 €)
        tx2 = tx_list[1]
        amt2 = tx2.find(f"{XML_NS}InstdAmt")
        self.assertEqual(amt2.text, "60.00")
        dbtr2 = tx2.find(f"{XML_NS}Dbtr/{XML_NS}Nm").text
        self.assertEqual(dbtr2, "Juergen Schroeder")
        iban2 = tx2.find(f"{XML_NS}DbtrAcct/{XML_NS}Id/{XML_NS}IBAN").text
        self.assertEqual(iban2, "DE12500105170648489890")

    def test_keine_offenen_mandate_wirft_validation_error(self):
        """Negativtest: Ein Jahr ohne offene SEPA-Posten wirft ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            erstelle_sepa_xml(2024)
        self.assertIn("keine offenen Beitragsposten", str(ctx.exception))

    @override_settings(SEPA_CREDITOR_ID="")
    def test_fehlende_glaeubiger_id_wirft_validation_error(self):
        """Negativtest: Ohne Gläubiger-ID kann keine SEPA-XML erzeugt werden."""
        with self.assertRaises(ValidationError) as ctx:
            erstelle_sepa_xml(2026)
        self.assertIn("Gläubiger-Identifikationsnummer", str(ctx.exception))

    def test_o_1_abfrage_budget(self):
        """Service darf keine N+1-Abfragen für Mandate oder Zahlungen machen."""
        with self.assertNumQueries(2):
            # Query 1: MembershipFee mit select_related member + sepa_mandat
            # Query 2: prefetch_related zahlungen
            erstelle_sepa_xml(2026)


class SepaExportViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_admin()
        cls.kategorie = FeeCategory.objects.create(name="Erwachsene")
        FeeAmount.objects.create(kategorie=cls.kategorie, jahr=2026, betrag=Decimal("90.00"))

        cls.member = Member.objects.create(
            vorname="Erika", nachname="Musterfrau",
            eintrittsdatum=date(2020, 1, 1), beitragskategorie=cls.kategorie,
        )
        cls.mandat = SepaMandate.objects.create(
            member=cls.member, referenz="MND-100",
            iban="DE89370400440532013000", kontoinhaber="Erika Musterfrau",
            erteilt_am=date(2025, 1, 1), status=SepaMandate.Status.AKTIV,
        )
        cls.fee = MembershipFee.objects.create(
            member=cls.member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_download_erzeugt_datei_und_audit_log(self):
        response = self.client.get("/beitraege/sepa-export.xml?jahr=2026")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        self.assertIn('attachment; filename="sepa-lastschrift-2026.xml"', response["Content-Disposition"])
        self.assertIn(b"urn:iso:std:iso:20022:tech:xsd:pain.008.001.02", response.content)

        # AuditLog-Prüfung (DSGVO N1.5)
        log = AuditLog.objects.filter(aktion="SEPA-XML-Export").latest("zeitpunkt")
        self.assertIn("Beitragsjahr 2026", log.text)
        self.assertIn("1 Posten", log.text)
        self.assertIn("90.00", log.text)
        # Keine Klartext-IBAN im AuditLog (ADR-010)
        self.assertNotIn("DE89370400440532013000", log.text)

    def test_download_leeres_jahr_meldet_fehler(self):
        """Negativtest: Download für Jahr ohne Posten leitet mit Fehlermeldung um."""
        response = self.client.get("/beitraege/sepa-export.xml?jahr=2023", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "keine offenen Beitragsposten mit aktivem SEPA-Mandat")

    def test_overview_zeigt_sepa_button_und_dialog(self):
        response = self.client.get("/beitraege/?jahr=2026")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SEPA-XML 2026")
        self.assertContains(response, 'id="sepa-dialog"')
        self.assertContains(response, 'action="/beitraege/sepa-export.xml"')
