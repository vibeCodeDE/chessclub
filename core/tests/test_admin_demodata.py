"""Tests für die Demo-Daten-Steuerung im Django Admin Panel (T34, S7.6, ADR-022).

Prüft:
- Zugriffsberechtigungen (Superadmin/Vorstand erlaubt; Mitglied/Kapitän abgewiesen).
- Reines Fachlogik-Verhalten in services.py (get_demo_data_status, install_demo_data, remove_demo_data).
- Laden von Demo-Daten per POST-Aktion inkl. AuditLog-Eintrag.
- Sicheres Entfernen per POST-Aktion mit Bestätigungs-Checkbox.
- Negativtests:
  - Löschen ohne Bestätigungs-Checkbox wird abgelehnt.
  - Löschen bei Vorhandensein echter Produktivdaten wird verweigert.
  - Nicht-berechtigte Nutzer werden abgewiesen.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog
from core.services import get_demo_data_status, install_demo_data, remove_demo_data
from members.models import Member

User = get_user_model()


class AdminDemoDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Gruppen sicherstellen
        for g_name in ("admin", "kapitaen", "mitglied"):
            Group.objects.get_or_create(name=g_name)

        cls.superuser = User.objects.create_superuser("superchef", "superchef@schach.de", "pass123")

        cls.vorstand = User.objects.create_user(
            "vorstand_test", "vorstand@schach.de", "pass123", is_staff=True
        )
        cls.vorstand.groups.add(Group.objects.get(name="admin"))

        cls.kapitaen = User.objects.create_user("kapitaen_test", "kapitaen@schach.de", "pass123")
        cls.kapitaen.groups.add(Group.objects.get(name="kapitaen"))

        cls.mitglied = User.objects.create_user("mitglied_test", "mitglied@schach.de", "pass123")
        cls.mitglied.groups.add(Group.objects.get(name="mitglied"))

        cls.changelist_url = reverse("admin:core_demodata_changelist")

    def test_admin_demodata_zugriff_fuer_superuser_erfolgreich(self):
        """Superuser kann die Demo-Daten-Verwaltungsseite öffnen."""
        self.client.force_login(self.superuser)
        res = self.client.get(self.changelist_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Demo-Daten")
        self.assertContains(res, "Demo-Daten jetzt laden")

    def test_admin_demodata_zugriff_fuer_admin_gruppe_erfolgreich(self):
        """Vorstands-Nutzer mit Staff-Status kann die Seite aufrufen."""
        self.client.force_login(self.vorstand)
        res = self.client.get(self.changelist_url)
        self.assertEqual(res.status_code, 200)

    def test_negativtest_mitglied_wird_abgewiesen(self):
        """Negativtest: Normales Mitglied ohne Staff-Rechte wird auf Admin-Login umgeleitet."""
        self.client.force_login(self.mitglied)
        res = self.client.get(self.changelist_url)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin/login/", res.headers.get("Location", ""))

    def test_negativtest_kapitaen_wird_abgewiesen(self):
        """Negativtest: Mannschaftsführer ohne Staff-Rechte wird abgewiesen."""
        self.client.force_login(self.kapitaen)
        res = self.client.get(self.changelist_url)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin/login/", res.headers.get("Location", ""))

    def test_install_demo_data_flow(self):
        """Laden der Demo-Daten über Admin-POST erzeugt Mitglieder und AuditLog."""
        self.client.force_login(self.superuser)
        self.assertEqual(Member.objects.count(), 0)

        res = self.client.post(self.changelist_url, {"action": "load"}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(Member.objects.count(), 45)
        self.assertTrue(
            AuditLog.objects.filter(aktion="Demo-Daten geladen", benutzer=self.superuser).exists()
        )

    def test_negativtest_remove_ohne_bestaetigung_wird_abgelehnt(self):
        """Negativtest: Entfernen ohne Checkbox führt zu Fehler und bricht ab."""
        self.client.force_login(self.superuser)
        install_demo_data(user=self.superuser)
        count_vorher = Member.objects.count()

        res = self.client.post(self.changelist_url, {"action": "remove"}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Bestätigung")
        self.assertEqual(Member.objects.count(), count_vorher)

    def test_remove_demo_data_flow_mit_bestaetigung(self):
        """Sicheres Entfernen der Demo-Daten leert die Beispieldaten und loggt im AuditLog."""
        self.client.force_login(self.superuser)
        install_demo_data(user=self.superuser)
        self.assertGreaterEqual(Member.objects.count(), 45)

        res = self.client.post(
            self.changelist_url,
            {"action": "remove", "confirm": "1"},
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Member.objects.count(), 0)
        self.assertTrue(
            AuditLog.objects.filter(aktion="Demo-Daten entfernt", benutzer=self.superuser).exists()
        )

    def test_negativtest_remove_bei_echten_daten_gesperrt(self):
        """Negativtest: Befinden sich echte Produktivdaten im System, wird das Löschen verweigert."""
        self.client.force_login(self.superuser)
        install_demo_data(user=self.superuser)

        from datetime import date
        Member.objects.create(
            vorname="Echter",
            nachname="Vereinsmensch",
            email="chef@echter-schachverein.de",
            strasse="Echte Str. 1",
            plz="12345",
            ort="Echtstadt",
            eintrittsdatum=date.today(),
        )

        res = self.client.post(
            self.changelist_url,
            {"action": "remove", "confirm": "1"},
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Schutz vor Datenverlust")
        # Mitgliedszahl unberührt
        self.assertTrue(Member.objects.filter(nachname="Vereinsmensch").exists())

    def test_services_fachfunktionen_direkt(self):
        """Reine Fachfunktionen in services.py liefern saubere Statuswerte und Rückgaben."""
        # 1. Status leer
        status_leer = get_demo_data_status()
        self.assertFalse(status_leer["is_active"])
        self.assertEqual(status_leer["total_members"], 0)
        self.assertTrue(status_leer["can_load"])

        # 2. Install
        ok, msg = install_demo_data(user=self.superuser)
        self.assertTrue(ok)
        self.assertIn("erfolgreich", msg)

        status_voll = get_demo_data_status()
        self.assertTrue(status_voll["is_active"])
        self.assertFalse(status_voll["has_real_data"])
        self.assertTrue(status_voll["can_remove"])

        # 3. Zweiter Install bricht ab
        ok2, msg2 = install_demo_data(user=self.superuser)
        self.assertFalse(ok2)

        # 4. Remove
        ok_del, msg_del = remove_demo_data(user=self.superuser, confirm=True)
        self.assertTrue(ok_del)
        self.assertEqual(Member.objects.count(), 0)
