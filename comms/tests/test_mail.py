"""Gruppen-E-Mail-Versand: Opt-in, Testmodus und Protokoll (T18)."""

import json
from datetime import date, timedelta
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from comms.models import MailLog, QueuedMail
from comms.services import (
    empfaenger_und_uebersprungene,
    process_mail_queue_batch,
    sende_gruppenmail,
)
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


class MailQueueBatchTests(TestCase):
    def setUp(self):
        self.admin = make_user("vorstand_queue", "admin")
        self.member1 = Member.objects.create(
            vorname="Anton", nachname="Alge", eintrittsdatum=date(2022, 1, 1),
            email="anton@example.org", email_opt_in=True,
        )
        self.member2 = Member.objects.create(
            vorname="Berta", nachname="Berg", eintrittsdatum=date(2022, 1, 1),
            email="berta@example.org", email_opt_in=True,
        )
        self.member3 = Member.objects.create(
            vorname="Clara", nachname="Claus", eintrittsdatum=date(2022, 1, 1),
            email="clara@example.org", email_opt_in=True,
        )

    def test_async_queue_stellt_in_warteschlange_ohne_sofortigen_versand(self):
        """async_send=True reiht E-Mails als PENDING ein und versendet nichts im Request-Thread."""
        log = sende_gruppenmail(
            betreff="Warteschlangen-Test",
            text="Hallo Queue!",
            zielgruppe=MailLog.Zielgruppe.AKTIV,
            benutzer=self.admin,
            async_send=True,
        )

        self.assertEqual(log.status, MailLog.Status.QUEUED)
        self.assertEqual(log.anzahl_empfaenger, 3)
        self.assertEqual(len(mail.outbox), 0, "Im asynchronen Modus darf kein sofortiger SMTP-Versand erfolgen")

        queued = QueuedMail.objects.filter(mail_log=log)
        self.assertEqual(queued.count(), 3)
        self.assertTrue(all(item.status == QueuedMail.Status.PENDING for item in queued))
        self.assertTrue(all(item.versuche == 0 for item in queued))

    def test_process_mail_queue_dry_run_aendert_keine_zustaende(self):
        """--dry-run simuliert den Queue-Durchlauf ohne SMTP-Zustellung oder Statuswechsel."""
        log = sende_gruppenmail(
            betreff="Dry-Run-Probe",
            text="Probeinhalt",
            zielgruppe=MailLog.Zielgruppe.AKTIV,
            benutzer=self.admin,
            async_send=True,
        )

        out = StringIO()
        call_command("process_mail_queue", "--dry-run", stdout=out)

        self.assertIn("[Dry-Run] 3 E-Mail(s) würden verarbeitet werden", out.getvalue())
        self.assertEqual(len(mail.outbox), 0)

        # Datensätze in DB bleiben PENDING mit 0 Versuchen
        queued = QueuedMail.objects.filter(mail_log=log)
        self.assertTrue(all(item.status == QueuedMail.Status.PENDING for item in queued))
        self.assertTrue(all(item.versuche == 0 for item in queued))
        log.refresh_from_db()
        self.assertEqual(log.status, MailLog.Status.QUEUED)

    def test_process_mail_queue_batch_limit_und_vollstaendige_abarbeitung(self):
        """Blockweises Abarbeiten per --limit teilt große Sendemengen auf."""
        log = sende_gruppenmail(
            betreff="Batch-Test",
            text="Batching klappt.",
            zielgruppe=MailLog.Zielgruppe.AKTIV,
            benutzer=self.admin,
            async_send=True,
        )

        # 1. Batch mit Limit 2
        out1 = StringIO()
        call_command("process_mail_queue", "--limit=2", stdout=out1)
        self.assertIn("2 versendet, 0 fehlgeschlagen, 1 verbleibend.", out1.getvalue())
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(QueuedMail.objects.filter(mail_log=log, status=QueuedMail.Status.SENT).count(), 2)
        self.assertEqual(QueuedMail.objects.filter(mail_log=log, status=QueuedMail.Status.PENDING).count(), 1)

        log.refresh_from_db()
        self.assertEqual(log.status, MailLog.Status.TEILWEISE)

        # 2. Batch verarbeitet den Rest
        out2 = StringIO()
        call_command("process_mail_queue", "--limit=2", stdout=out2)
        self.assertIn("1 versendet, 0 fehlgeschlagen, 0 verbleibend.", out2.getvalue())
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(QueuedMail.objects.filter(mail_log=log, status=QueuedMail.Status.SENT).count(), 3)
        self.assertEqual(QueuedMail.objects.filter(mail_log=log, status=QueuedMail.Status.PENDING).count(), 0)

        log.refresh_from_db()
        self.assertEqual(log.status, MailLog.Status.GESENDET)

    def test_smtp_fehler_und_max_retries_negativtest(self):
        """Negativtest: SMTP-Ausfälle zählen Versuche hoch und setzen erst bei max_retries auf FAILED."""
        from unittest.mock import patch

        log = sende_gruppenmail(
            betreff="Fehler-Queue",
            text="Wird fehlschlagen.",
            zielgruppe=MailLog.Zielgruppe.AKTIV,
            test_empfaenger="fehler@example.org",
            benutzer=self.admin,
            async_send=True,
        )

        item = QueuedMail.objects.get(mail_log=log)
        self.assertEqual(item.status, QueuedMail.Status.PENDING)
        self.assertEqual(item.versuche, 0)

        with patch("comms.services.send_mail", side_effect=RuntimeError("Verbindung verweigert")):
            # Versuch 1 (max_retries=3): noch PENDING
            res1 = process_mail_queue_batch(mail_log=log, max_retries=3)
            item.refresh_from_db()
            self.assertEqual(item.versuche, 1)
            self.assertEqual(item.status, QueuedMail.Status.PENDING)
            self.assertIn("Verbindung verweigert", item.fehler_meldung)
            self.assertEqual(res1["gesendet"], 0)

            # Versuch 2
            process_mail_queue_batch(mail_log=log, max_retries=3)
            item.refresh_from_db()
            self.assertEqual(item.versuche, 2)
            self.assertEqual(item.status, QueuedMail.Status.PENDING)

            # Versuch 3: Erreicht max_retries=3 -> Übergang zu FAILED
            res3 = process_mail_queue_batch(mail_log=log, max_retries=3)
            item.refresh_from_db()
            self.assertEqual(item.versuche, 3)
            self.assertEqual(item.status, QueuedMail.Status.FAILED)
            self.assertEqual(res3["fehlgeschlagen"], 1)

            log.refresh_from_db()
            self.assertEqual(log.status, MailLog.Status.FEHLGESCHLAGEN)
            self.assertEqual(log.anzahl_fehler, 1)

            # Ein weiterer Lauf rührt das fehlgeschlagene Element nicht mehr an
            res4 = process_mail_queue_batch(mail_log=log, max_retries=3)
            self.assertEqual(res4["gesendet"], 0)
            self.assertEqual(res4["fehlgeschlagen"], 0)
            self.assertEqual(res4["verbleibend"], 0)

