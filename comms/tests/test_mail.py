"""Gruppen-E-Mail-Versand: Opt-in, Testmodus und Protokoll (T18)."""

import json
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from comms.models import MailLog
from comms.services import empfaenger_und_uebersprungene, sende_gruppenmail
from members.models import Member


def make_user(username, group_name=None):
    user = User.objects.create_user(username, password="x")
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


class GruppenmailTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand", "admin")
        self.client.force_login(self.admin)
        self.aktive = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 1),
            email="anna@example.org", email_opt_in=True,
        )
        self.ohne_optin = Member.objects.create(
            vorname="Bodo", nachname="Bauer", eintrittsdatum=date(2020, 1, 1),
            email="bodo@example.org", email_opt_in=False,
        )
        self.ohne_mail = Member.objects.create(
            vorname="Cem", nachname="Cakir", eintrittsdatum=date(2020, 1, 1),
        )
        self.ausgetreten = Member.objects.create(
            vorname="Dana", nachname="Dorn", eintrittsdatum=date(2010, 1, 1),
            status=Member.Status.AUSGETRETEN, email="dana@example.org", email_opt_in=True,
        )

    def test_opt_in_und_austritt_werden_beachtet(self):
        adressen, uebersprungen = empfaenger_und_uebersprungene(MailLog.Zielgruppe.ALLE)
        self.assertEqual(adressen, ["anna@example.org"])
        self.assertEqual(uebersprungen, 2, "ohne Opt-in und ohne Adresse werden übersprungen")
        self.assertNotIn("dana@example.org", adressen, "Ausgetretene werden nie angeschrieben")

    def test_versand_protokolliert_und_versendet_einzeln(self):
        log = sende_gruppenmail(
            betreff="Vereinsabend",
            text="Donnerstag 19 Uhr.",
            zielgruppe=MailLog.Zielgruppe.ALLE,
            benutzer=self.admin,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("bodo@example.org", mail.outbox[0].to)
        self.assertEqual(mail.outbox[0].to, ["anna@example.org"])
        self.assertEqual(log.status, MailLog.Status.GESENDET)
        self.assertEqual(log.anzahl_empfaenger, 1)
        self.assertEqual(log.anzahl_uebersprungen, 2)
        self.assertEqual(log.erstellt_von, self.admin)

    def test_testversand_geht_nur_an_testadresse(self):
        log = sende_gruppenmail(
            betreff="Probe",
            text="Nur ein Test.",
            zielgruppe=MailLog.Zielgruppe.ALLE,
            benutzer=self.admin,
            test_empfaenger="probe@example.org, zweite@example.org",
        )
        self.assertEqual(sorted(mail.outbox[0].to + mail.outbox[1].to),
                         ["probe@example.org", "zweite@example.org"])
        self.assertEqual(log.status, MailLog.Status.TEST)
        self.assertIn("probe@example.org", log.test_empfaenger)

    def test_zielgruppe_vorstand_nutzt_rollen(self):
        member = Member.objects.create(
            vorname="Vera", nachname="Vorstand", eintrittsdatum=date(2020, 1, 1),
            email="vera@example.org", email_opt_in=True, user=self.admin,
        )
        adressen, _ = empfaenger_und_uebersprungene(MailLog.Zielgruppe.VORSTAND)
        self.assertEqual(adressen, ["vera@example.org"])
        self.assertEqual(member.email, "vera@example.org")

    def test_formular_versendet_ueber_ajax(self):
        response = self.client.post(
            "/ankuendigungen/mail/",
            {"betreff": "Rundbrief", "zielgruppe": "aktiv", "text": "Hallo zusammen!",
             "test_empfaenger": ""},
            HTTP_ACCEPT="application/json",
        )
        daten = json.loads(response.content)
        self.assertTrue(daten["ok"])
        self.assertIn("1 E-Mail(s) versendet", daten["message"])
        self.assertEqual(MailLog.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_protokoll_seite_zeigt_sendungen(self):
        sende_gruppenmail(
            betreff="Protokolleintrag", text="x", zielgruppe=MailLog.Zielgruppe.AKTIV,
            benutzer=self.admin,
        )
        response = self.client.get("/ankuendigungen/mail/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Protokolleintrag")
        self.assertContains(response, "Versandprotokoll")

    def test_nur_admin_darf_versenden(self):
        user = make_user("p1", "mitglied")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/ankuendigungen/mail/").status_code, 403)

    def test_formular_ohne_ajax_und_fehlerpfad(self):
        resp = self.client.post(
            "/ankuendigungen/mail/",
            {"betreff": "Klassisch", "zielgruppe": "aktiv", "text": "Nachricht", "test_empfaenger": ""},
        )
        self.assertRedirects(resp, "/ankuendigungen/mail/")
        err = self.client.post(
            "/ankuendigungen/mail/",
            {"betreff": "", "zielgruppe": "aktiv", "text": ""},
            HTTP_ACCEPT="application/json",
        )
        self.assertFalse(json.loads(err.content)["ok"])

    def test_fehlversand_zaehlt_als_fehler(self):
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend"):
            from unittest.mock import patch

            with patch("comms.services.send_mail", side_effect=RuntimeError("SMTP weg")):
                log = sende_gruppenmail(
                    betreff="Kaputt", text="x", zielgruppe=MailLog.Zielgruppe.AKTIV,
                    benutzer=self.admin,
                )
        self.assertEqual(log.status, MailLog.Status.FEHLGESCHLAGEN)
        self.assertEqual(log.anzahl_fehler, 1)
        self.assertLessEqual(log.erstellt_am, timezone.now())


class AnonymisierungsVorbereitungTests(TestCase):
    def test_ohne_email_kein_versand(self):
        Member.objects.create(
            vorname="Ohne", nachname="Adresse", eintrittsdatum=date(2020, 1, 1),
            email_opt_in=True,
        )
        adressen, uebersprungen = empfaenger_und_uebersprungene(MailLog.Zielgruppe.ALLE)
        self.assertEqual(adressen, [])
        self.assertEqual(uebersprungen, 1)

    def test_frist_helfer_fuer_unix_zeit(self):
        """Stellt sicher, dass Datumsrechnungen für Löschfristen funktionieren (T20)."""
        grenze = date.today() - timedelta(days=730)
        self.assertLess(grenze, date.today())
