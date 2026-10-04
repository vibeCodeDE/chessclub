"""DSGVO: Datenauskunft, Verzeichnis und Anonymisierung nach Frist (T20)."""

import csv
import io
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase

from core.dsgvo import ANONYMISIERUNGS_FRIST_TAGE, anonymisierungs_kandidaten
from core.models import AuditLog
from dues.models import MembershipFee, Payment, SepaMandate
from members.models import Member
from teams.models import LeagueMatch, LineupEntry, Team


def make_admin(username="vorstand"):
    user = User.objects.create_user(username, password="x")
    group, _ = Group.objects.get_or_create(name="admin")
    user.groups.add(group)
    return user


class DatenauskunftTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.force_login(self.admin)
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", geburtsdatum=date(1985, 3, 2),
            strasse="Hauptstraße 1", plz="37073", ort="Musterstadt",
            email="anna@example.org", telefon="030 123456", eintrittsdatum=date(2020, 1, 15),
        )
        self.fee = MembershipFee.objects.create(
            member=self.member, jahr=2026, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2026, 1, 31),
        )
        Payment.objects.create(fee=self.fee, betrag=Decimal("90.00"), datum=date(2026, 2, 1))
        SepaMandate.objects.create(
            member=self.member, referenz="SCKS-2026-001", iban="DE89370400440532013000",
            erteilt_am=date(2026, 1, 5),
        )
        team = Team.objects.create(name="1. Mannschaft", liga="Bezirksliga", brettanzahl=4)
        match = LeagueMatch.objects.create(team=team, datum=date(2026, 3, 1), gegner="SV Test")
        LineupEntry.objects.create(match=match, brett=1, member=self.member)

    def test_auskunft_enthaelt_alle_kategorien(self):
        response = self.client.get(f"/mitglieder/{self.member.pk}/auskunft/")
        self.assertEqual(response.status_code, 200)
        inhalt = response.content.decode()
        for erwartet in [
            "Anna", "Meier", "anna@example.org", "Hauptstraße 1",
            "SCKS-2026-001", "90,00", "SV Test", "Statusverlauf", "Protokolle",
        ]:
            self.assertIn(erwartet, inhalt)

    def test_zugriff_wird_protokolliert(self):
        self.client.get(f"/mitglieder/{self.member.pk}/auskunft/")
        eintrag = AuditLog.objects.filter(aktion="Datenauskunft erstellt").first()
        self.assertIsNotNone(eintrag)
        self.assertEqual(eintrag.member, self.member)
        self.assertEqual(eintrag.benutzer, self.admin)

    def test_pdf_auskunft_ist_ein_pdf_und_wird_protokolliert(self):
        """PRD N1.2: ein Klick → vollständiges PDF."""
        response = self.client.get(f"/mitglieder/{self.member.pk}/auskunft.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"), "Antwort ist kein PDF")
        self.assertGreater(len(response.content), 3000, "PDF wirkt leer")
        self.assertTrue(
            AuditLog.objects.filter(aktion="Datenauskunft erstellt", member=self.member).exists()
        )

    def test_pdf_auskunft_ohne_javascript_und_mit_daten_ohne_mandat(self):
        """Auch Mitglieder ohne Mandat/Zahlungen erzeugen ein gültiges PDF."""
        schlicht = Member.objects.create(
            vorname="Ohne", nachname="Mandat", eintrittsdatum=date(2020, 1, 1)
        )
        response = self.client.get(f"/mitglieder/{schlicht.pk}/auskunft.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_json_export_ist_maschinenlesbar(self):
        response = self.client.get(f"/mitglieder/{self.member.pk}/auskunft.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        daten = json.loads(response.content.decode())
        self.assertEqual(daten["daten"]["stammdaten"]["email"], "anna@example.org")
        self.assertEqual(len(daten["daten"]["beitraege"]), 1)
        self.assertEqual(daten["daten"]["sepa_mandat"]["referenz"], "SCKS-2026-001")
        eintrag = AuditLog.objects.filter(aktion="Datenauskunft erstellt", member=self.member).first()
        self.assertIsNotNone(eintrag, "JSON-Datenauskunft muss im Audit-Log protokolliert werden")
        self.assertEqual(eintrag.benutzer, self.admin)
        self.assertIn("JSON", eintrag.text)

    def test_mitgliedsakte_und_csv_export_werden_protokolliert(self):
        """PRD N1.5: Zugriffe auf Personendaten und Exporte werden protokolliert."""
        detail_resp = self.client.get(f"/mitglieder/{self.member.pk}/")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(
                aktion="Mitgliedsakte eingesehen", member=self.member, benutzer=self.admin
            ).exists()
        )

        export_resp = self.client.get("/mitglieder/export.csv")
        self.assertEqual(export_resp.status_code, 200)
        self.assertTrue(
            AuditLog.objects.filter(
                aktion="Mitgliederliste exportiert", benutzer=self.admin
            ).exists()
        )

    def test_verzeichnis_csv_listet_datenkategorien(self):
        response = self.client.get("/datenschutz/verzeichnis.csv")
        self.assertEqual(response.status_code, 200)
        zeilen = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
        kategorien = [zeile[0] for zeile in zeilen[1:]]
        self.assertIn("Stammdaten", kategorien)
        self.assertIn("Beitragsdaten", kategorien)
        self.assertIn("SEPA-Mandat", kategorien)

    def test_mitglied_ohne_rechte_erhaelt_403(self):
        user = User.objects.create_user("p1", password="x")
        group, _ = Group.objects.get_or_create(name="mitglied")
        user.groups.add(group)
        self.client.force_login(user)

        for endpunkt in [
            f"/mitglieder/{self.member.pk}/auskunft/",
            f"/mitglieder/{self.member.pk}/auskunft.pdf",
            f"/mitglieder/{self.member.pk}/auskunft.json",
        ]:
            with self.subTest(endpunkt=endpunkt):
                AuditLog.objects.all().delete()
                response = self.client.get(endpunkt)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(AuditLog.objects.count(), 0)

    def test_mitglied_darf_eigene_auskunft_herunterladen(self):
        """PRD §3.8: Auskunfts-Export (DSGVO) – Mitglied: nur eigene Person."""
        user = User.objects.create_user("eigenes_mitglied", password="x")
        group, _ = Group.objects.get_or_create(name="mitglied")
        user.groups.add(group)
        self.member.user = user
        self.member.save()
        self.client.force_login(user)

        # HTML
        resp = self.client.get(f"/mitglieder/{self.member.pk}/auskunft/")
        self.assertEqual(resp.status_code, 200)

        # PDF
        resp_pdf = self.client.get(f"/mitglieder/{self.member.pk}/auskunft.pdf")
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf["Content-Type"], "application/pdf")

        # JSON
        resp_json = self.client.get(f"/mitglieder/{self.member.pk}/auskunft.json")
        self.assertEqual(resp_json.status_code, 200)
        self.assertEqual(resp_json["Content-Type"], "application/json; charset=utf-8")

        # Protokolliert
        self.assertTrue(
            AuditLog.objects.filter(aktion="Datenauskunft erstellt", member=self.member, benutzer=user).exists()
        )

    def test_kapitaen_erhaelt_403_auf_auskunft(self):
        user = User.objects.create_user("k1", password="x")
        group, _ = Group.objects.get_or_create(name="kapitaen")
        user.groups.add(group)
        self.client.force_login(user)

        for endpunkt in [
            f"/mitglieder/{self.member.pk}/auskunft/",
            f"/mitglieder/{self.member.pk}/auskunft.pdf",
            f"/mitglieder/{self.member.pk}/auskunft.json",
        ]:
            with self.subTest(endpunkt=endpunkt):
                AuditLog.objects.all().delete()
                response = self.client.get(endpunkt)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(AuditLog.objects.count(), 0)

    def test_audit_eintraege_aufbewahrungsfrist_filterbar(self):
        """PRD N1.5: Audit-Einträge sind nach 12 Monaten Aufbewahrungsfrist markierbar/filterbar."""
        from django.utils import timezone

        alt_zeitpunkt = timezone.now() - timedelta(days=370)
        frisch_zeitpunkt = timezone.now() - timedelta(days=30)

        eintrag_alt = AuditLog.objects.create(
            benutzer=self.admin,
            aktion="Datenauskunft erstellt",
            text="Auskunft alt",
            member=self.member,
        )
        AuditLog.objects.filter(pk=eintrag_alt.pk).update(zeitpunkt=alt_zeitpunkt)
        eintrag_alt.refresh_from_db()

        eintrag_frisch = AuditLog.objects.create(
            benutzer=self.admin,
            aktion="Datenauskunft erstellt",
            text="Auskunft frisch",
            member=self.member,
        )
        AuditLog.objects.filter(pk=eintrag_frisch.pk).update(zeitpunkt=frisch_zeitpunkt)
        eintrag_frisch.refresh_from_db()

        abgelaufen = list(AuditLog.objects.aufbewahrungsfrist_abgelaufen(tage=365))
        self.assertIn(eintrag_alt, abgelaufen)
        self.assertNotIn(eintrag_frisch, abgelaufen)
        self.assertTrue(eintrag_alt.aufbewahrungsfrist_abgelaufen)
        self.assertFalse(eintrag_frisch.aufbewahrungsfrist_abgelaufen)


class AnonymisierungTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.frist = ANONYMISIERUNGS_FRIST_TAGE
        alt = date.today() - timedelta(days=self.frist + 10)

        self.alt = Member.objects.create(
            vorname="Alt", nachname="Ehemalig", geburtsdatum=date(1960, 1, 1),
            strasse="Altweg 3", plz="37073", ort="Musterstadt",
            email="alt@example.org", telefon="030 000000",
            eintrittsdatum=date(2000, 1, 1), status=Member.Status.AUSGETRETEN,
            austrittsdatum=alt,
        )
        MembershipFee.objects.create(
            member=self.alt, jahr=2024, kategorie_name="Erwachsene",
            betrag=Decimal("90.00"), faellig_am=date(2024, 1, 31),
        )
        self.frisch = Member.objects.create(
            vorname="Neu", nachname="Ehemalig", eintrittsdatum=date(2000, 1, 1),
            status=Member.Status.AUSGETRETEN, austrittsdatum=date.today() - timedelta(days=10),
            email="neu@example.org",
        )

    def test_kandidaten_nur_nach_fristablauf(self):
        kandidaten = list(anonymisierungs_kandidaten())
        self.assertIn(self.alt, kandidaten)
        self.assertNotIn(self.frisch, kandidaten)

    def test_dry_run_aendert_nichts(self):
        call_command("anonymize_former_members", "--dry-run", verbosity=0)
        self.alt.refresh_from_db()
        self.assertEqual(self.alt.nachname, "Ehemalig")
        self.assertEqual(self.alt.email, "alt@example.org")

    def test_anonymisierung_entfernt_kontaktdaten_behaelt_finanzen(self):
        call_command("anonymize_former_members", verbosity=0)
        self.alt.refresh_from_db()
        self.assertEqual(self.alt.vorname, "Ehemaliges")
        self.assertEqual(self.alt.nachname, "Mitglied")
        self.assertIsNone(self.alt.geburtsdatum)
        self.assertEqual(self.alt.email, "")
        self.assertEqual(self.alt.telefon, "")
        self.assertEqual(self.alt.strasse, "")
        self.assertIsNotNone(self.alt.anonymisiert_am)
        self.assertEqual(self.alt.fees.count(), 1, "Finanzhistorie bleibt erhalten")
        self.assertTrue(AuditLog.objects.filter(aktion="Mitglied anonymisiert").exists())

        self.frisch.refresh_from_db()
        self.assertEqual(self.frisch.email, "neu@example.org", "Frist läuft noch")

    def test_bereits_anonymisierte_werden_uebersprungen(self):
        call_command("anonymize_former_members", verbosity=0)
        ausgabe = io.StringIO()
        call_command("anonymize_former_members", verbosity=0, stdout=ausgabe)
        self.assertIn("Keine Kandidat:innen", ausgabe.getvalue())
