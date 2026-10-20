"""Die IBAN liegt verschlüsselt in der Datenbank (ADR-010).

Zwei Dinge müssen gleichzeitig stimmen: In der Datenbank steht **kein**
Klartext, und die Oberfläche zeigt trotzdem die nötigen Angaben (Maske in
Listen, Klartext nur in der Auskunft der betroffenen Person). Ohne Schlüssel
darf die App nicht stillschweigend auf Klartext zurückfallen.
"""

from datetime import date

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, override_settings

from dues.crypto import entschluesseln, ist_chiffre, verschluesseln
from dues.models import SepaMandate
from members.models import Member

IBAN = "DE89370400440532013000"
ANDERER_SCHLUESSEL = Fernet.generate_key().decode()


def rohwert(pk):
    """Den tatsächlich gespeicherten Wert lesen, ohne Entschlüsselung."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT iban, iban_kurz FROM dues_sepamandate WHERE id = %s", [pk])
        return cursor.fetchone()


class ChiffreTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(
            vorname="Anna", nachname="Meier", eintrittsdatum=date(2020, 1, 15)
        )

    def mandat(self, iban=IBAN):
        return SepaMandate.objects.create(
            member=self.member, referenz="SCKS-2026-001", iban=iban, erteilt_am=date(2026, 1, 5)
        )

    def test_in_der_datenbank_steht_kein_klartext(self):
        mandat = self.mandat()

        gespeichert, _ = rohwert(mandat.pk)

        self.assertTrue(ist_chiffre(gespeichert))
        self.assertNotIn(IBAN, gespeichert)
        self.assertNotIn("37040044", gespeichert)

    def test_gelesen_wird_wieder_entschluesselt(self):
        mandat = self.mandat()

        gespeichert, _ = rohwert(mandat.pk)
        neu_geladen = SepaMandate.objects.get(pk=mandat.pk)

        self.assertEqual(neu_geladen.iban, IBAN)
        self.assertEqual(entschluesseln(gespeichert), IBAN)

    def test_gleiche_iban_wird_zweimal_verschieden_gespeichert(self):
        """Kein Chiffretext ist wiederholbar – das ist der Preis der Suche
        (ADR-010: Suche auf IBAN ist bewusst nicht möglich)."""
        a = verschluesseln(IBAN)
        b = verschluesseln(IBAN)

        self.assertNotEqual(a, b)
        self.assertEqual(entschluesseln(a), IBAN)
        self.assertEqual(entschluesseln(b), IBAN)

    def test_maske_steht_im_klartext_in_der_datenbank(self):
        mandat = self.mandat()

        _, maske = rohwert(mandat.pk)

        self.assertEqual(maske, "DE89 •••• •••• 3000")
        self.assertEqual(mandat.iban_kurz, "DE89 •••• •••• 3000")
        self.assertNotIn(IBAN, maske)

    def test_leere_iban_wird_nicht_verschluesselt(self):
        SepaMandate.objects.create(
            member=self.member, referenz="SCKS-2026-003", iban="", erteilt_am=date(2026, 1, 5)
        )

        gespeichert, maske = rohwert(self.member.sepa_mandat.pk)

        self.assertEqual(gespeichert, "")
        self.assertEqual(maske, "")

    @override_settings(IBAN_FERNET_KEY="")
    def test_ohne_schluessel_bricht_der_zugriff_ab(self):
        """Negativtest: kein stiller Rückfall auf Klartext."""
        with self.assertRaises(ImproperlyConfigured):
            verschluesseln(IBAN)

    def test_falscher_schluessel_meldet_klar_und_verliert_nichts(self):
        """Negativtest: Der Betrieb darf die Daten nicht verlieren, nur weil
        jemand den falschen Schlüssel eingetragen hat."""
        # Erst mit dem richtigen Schlüssel schreiben, dann erst den Schlüssel
        # tauschen – sonst entstünde das Mandat schon mit dem falschen.
        mandat = self.mandat()
        gespeichert, _ = rohwert(mandat.pk)

        with override_settings(IBAN_FERNET_KEY=ANDERER_SCHLUESSEL):
            with self.assertRaises(ImproperlyConfigured) as fehler:
                SepaMandate.objects.get(pk=mandat.pk)

        self.assertIn("IBAN_FERNET_KEY", str(fehler.exception))
        # Der Chiffretext in der Datenbank ist unverändert – die Daten sind da.
        unveraendert, _ = rohwert(mandat.pk)
        self.assertEqual(unveraendert, gespeichert)

    def test_formular_speichert_klartext_in_der_maske(self):
        """Der Vorstand pflegt wie bisher; nur die Datenbank sieht Chiffretext."""
        self.client.force_login(_admin())
        self.client.post(
            "/beitraege/mandate/neu/",
            {
                "member": self.member.pk,
                "referenz": "SCKS-2026-004",
                "iban": "de89 3704 0044 0532 0130 00",
                "kontoinhaber": "Anna Meier",
                "erteilt_am": "05.01.2026",
                "status": "aktiv",
                "notiz": "",
            },
        )

        gespeichert, maske = rohwert(self.member.sepa_mandat.pk)

        self.assertTrue(ist_chiffre(gespeichert))
        self.assertEqual(maske, "DE89 •••• •••• 3000")
        self.assertEqual(self.member.sepa_mandat.iban, IBAN)

    def test_admin_change_view_protokolliert_zugriff_im_audit_log(self):
        from django.contrib.auth.models import User
        from core.models import AuditLog

        admin_user = User.objects.create_superuser("admin_root", password="x")
        mandat = self.mandat()

        self.client.force_login(admin_user)
        response = self.client.get(f"/admin/dues/sepamandate/{mandat.pk}/change/")
        self.assertEqual(response.status_code, 200)

        eintrag = AuditLog.objects.filter(aktion="SEPA-Mandat eingesehen", member=self.member).first()
        self.assertIsNotNone(eintrag)
        self.assertEqual(eintrag.benutzer, admin_user)
        self.assertIn(mandat.referenz, eintrag.text)


def _admin():
    from django.contrib.auth.models import Group, User

    user = User.objects.create_user("vorstand", password="x")
    user.groups.add(Group.objects.get_or_create(name="admin")[0])
    return user
