"""Tests für Modul-Toggles im Admin-Panel (T30 / S7.4 / ADR-019)."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from cashbook.models import CashEntry
from comms.models import NewsPost
from core.models import AuditLog, ModuleSettings
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, MITGLIED_GROUP
from core.services import is_module_active, set_module_status
from dues.models import FeeCategory, MembershipFee
from dues.services import zahlung_erfassen
from members.models import Member
from tournaments.models import Tournament


def make_user(username, group_name="mitglied", staff=False, superuser=False):
    user = User.objects.create_user(
        username=username,
        password="x",
        email=f"{username}@example.com",
        is_staff=staff,
        is_superuser=superuser,
    )
    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


class ModuleSettingsModelTests(TestCase):
    def test_singleton_get_solo_und_defaults(self):
        settings = ModuleSettings.get_solo()
        self.assertEqual(settings.pk, 1)
        self.assertTrue(settings.homepage_aktiv)
        self.assertTrue(settings.spielbetrieb_aktiv)
        self.assertTrue(settings.turniere_aktiv)
        self.assertTrue(settings.kassenbuch_aktiv)
        self.assertTrue(settings.nachrichten_aktiv)

    def test_save_erzwingt_pk_1(self):
        settings = ModuleSettings(pk=99, spielbetrieb_aktiv=False)
        settings.save()
        self.assertEqual(settings.pk, 1)
        self.assertEqual(ModuleSettings.objects.count(), 1)

    def test_kernmodule_immer_aktiv(self):
        self.assertTrue(is_module_active("core"))
        self.assertTrue(is_module_active("members"))
        self.assertTrue(is_module_active("dues"))
        self.assertTrue(is_module_active("unbekanntes_modul"))

    def test_set_module_status_schreibt_audit_log(self):
        admin = make_user("admin1", ADMIN_GROUP)
        settings = set_module_status("teams", False, user=admin)
        self.assertFalse(settings.spielbetrieb_aktiv)
        self.assertFalse(is_module_active("teams"))

        eintrag = AuditLog.objects.filter(aktion="Modul-Einstellungen geändert").first()
        self.assertIsNotNone(eintrag)
        self.assertEqual(eintrag.benutzer, admin)
        self.assertEqual(eintrag.feld, "spielbetrieb_aktiv")
        self.assertEqual(eintrag.neu_wert, "False")

    def test_homepage_modul_schluessel_und_status(self):
        admin = make_user("admin_hp", ADMIN_GROUP)
        settings = set_module_status("homepage", False, user=admin)
        self.assertFalse(settings.homepage_aktiv)
        self.assertFalse(is_module_active("homepage"))
        self.assertFalse(is_module_active("vereinshomepage"))
        self.assertFalse(is_module_active("webseite"))


class ModuleSettingsAdminTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin_user", ADMIN_GROUP, staff=True, superuser=True)
        self.mitglied = make_user("normal_user", MITGLIED_GROUP)
        self.kapitaen = make_user("kapitaen_user", KAPITAEN_GROUP)
        self.cfg = ModuleSettings.get_solo()

    def test_admin_kann_einstellungen_aendern_und_erzeugt_audit(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/admin/core/modulesettings/{self.cfg.pk}/change/",
            {
                "homepage_aktiv": "on",
                "spielbetrieb_aktiv": "on",
                "turniere_aktiv": "on",
                # Kassenbuch und News abgewählt
            },
        )
        self.assertRedirects(response, "/admin/core/modulesettings/")
        self.cfg.refresh_from_db()
        self.assertTrue(self.cfg.homepage_aktiv)
        self.assertTrue(self.cfg.spielbetrieb_aktiv)
        self.assertTrue(self.cfg.turniere_aktiv)
        self.assertFalse(self.cfg.kassenbuch_aktiv)
        self.assertFalse(self.cfg.nachrichten_aktiv)

        eintrag = AuditLog.objects.filter(aktion="Modul-Einstellungen geändert").first()
        self.assertIsNotNone(eintrag)
        self.assertEqual(eintrag.benutzer, self.admin)
        self.assertIn("kassenbuch_aktiv", eintrag.text)
        self.assertIn("nachrichten_aktiv", eintrag.text)

    def test_nicht_admin_darf_modul_einstellungen_nicht_aufrufen(self):
        """Negativtest (Berechtigungsmatrix §3.8): Mitglied und Kapitän erhalten 302/403."""
        for user in (self.mitglied, self.kapitaen):
            self.client.force_login(user)
            response = self.client.get(f"/admin/core/modulesettings/{self.cfg.pk}/change/")
            self.assertIn(response.status_code, (302, 403))


class ModuleNavigationTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin_nav", ADMIN_GROUP, staff=True)
        self.cfg = ModuleSettings.get_solo()

    def test_navigation_blendet_inaktive_module_aus(self):
        self.client.force_login(self.admin)

        # 1. Alles aktiv
        response = self.client.get("/dashboard/")
        self.assertContains(response, 'href="/kasse/"')
        self.assertContains(response, 'href="/turniere/verwalten/"')
        self.assertContains(response, 'href="/mannschaften/"')
        self.assertContains(response, 'href="/ankuendigungen/"')

        # 2. Kassenbuch und Turniere deaktivieren
        self.cfg.kassenbuch_aktiv = False
        self.cfg.turniere_aktiv = False
        self.cfg.save()

        response = self.client.get("/dashboard/")
        self.assertNotContains(response, 'href="/kasse/"')
        self.assertNotContains(response, 'href="/turniere/verwalten/"')
        # Sektion Turniere komplett ausgeblendet
        self.assertNotIn("Turnierverwaltung", [link["label"] for link in response.context["nav_links"]])

        # 3. Spielbetrieb und News deaktivieren
        self.cfg.spielbetrieb_aktiv = False
        self.cfg.nachrichten_aktiv = False
        self.cfg.save()

        response = self.client.get("/dashboard/")
        self.assertNotContains(response, 'href="/mannschaften/"')
        self.assertNotContains(response, 'href="/ankuendigungen/"')
        self.assertNotContains(response, 'href="/meine-einsaetze/"')

        # 4. Homepage deaktivieren -> Vereinsseite ausgeblendet
        self.cfg.homepage_aktiv = False
        self.cfg.save()

        response = self.client.get("/dashboard/")
        self.assertNotIn("Vereinsseite", [link["label"] for link in response.context["nav_links"]])


class ModuleUrlBlockTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin_url", ADMIN_GROUP, staff=True)
        self.cfg = ModuleSettings.get_solo()

    def test_inaktive_module_liefern_404(self):
        """Negativtest: Direkter URL-Aufruf liefert 404, wenn Modul deaktiviert ist."""
        self.client.force_login(self.admin)

        # Deaktivieren
        self.cfg.spielbetrieb_aktiv = False
        self.cfg.turniere_aktiv = False
        self.cfg.kassenbuch_aktiv = False
        self.cfg.nachrichten_aktiv = False
        self.cfg.save()

        # Teams-URLs -> 404
        self.assertEqual(self.client.get("/mannschaften/").status_code, 404)
        self.assertEqual(self.client.get("/spiele/").status_code, 404)
        self.assertEqual(self.client.get("/ligen/").status_code, 404)
        self.assertEqual(self.client.get("/meine-einsaetze/").status_code, 404)

        # Turniere-URLs -> 404
        self.assertEqual(self.client.get("/turniere/").status_code, 404)
        self.assertEqual(self.client.get("/turniere/verwalten/").status_code, 404)

        # Kassenbuch-URLs -> 404
        self.assertEqual(self.client.get("/kasse/").status_code, 404)
        self.assertEqual(self.client.get("/kasse/neu/").status_code, 404)

        # News-URLs -> 404
        self.assertEqual(self.client.get("/ankuendigungen/").status_code, 404)
        self.assertEqual(self.client.get("/ankuendigungen/mail/").status_code, 404)
        self.assertEqual(self.client.get("/aktuelles/").status_code, 404)

    def test_homepage_modul_routing_und_404(self):
        """Negativtest: /verein/ liefert 404 bei deaktivierter Homepage; / leitet je nach Login um."""
        # 1. Aktiv:
        self.cfg.homepage_aktiv = True
        self.cfg.save()
        self.assertEqual(self.client.get("/verein/").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 200)

        # 2. Deaktiviert:
        self.cfg.homepage_aktiv = False
        self.cfg.save()

        # Gast: /verein/ liefert 404, / leitet zum Login (302)
        self.assertEqual(self.client.get("/verein/").status_code, 404)
        res_anon = self.client.get("/")
        self.assertEqual(res_anon.status_code, 302)
        self.assertEqual(res_anon.url, "/anmelden/")

        # Eingeloggt: / leitet zum Dashboard (302)
        self.client.force_login(self.admin)
        res_auth = self.client.get("/")
        self.assertEqual(res_auth.status_code, 302)
        self.assertEqual(res_auth.url, "/dashboard/")

    def test_reaktivierung_macht_urls_wieder_erreichbar(self):
        self.client.force_login(self.admin)
        self.cfg.kassenbuch_aktiv = False
        self.cfg.save()
        self.assertEqual(self.client.get("/kasse/").status_code, 404)

        self.cfg.kassenbuch_aktiv = True
        self.cfg.save()
        self.assertEqual(self.client.get("/kasse/").status_code, 200)


class ModuleSucheUndDashboardTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin_suche", ADMIN_GROUP)
        self.cfg = ModuleSettings.get_solo()
        Tournament.objects.create(name="Herbstturnier", datum=date(2026, 10, 20), status="geplant")
        NewsPost.objects.create(titel="Wichtige Neuigkeiten", text="Test", veroeffentlicht=True)

    def test_suche_ignoriert_inaktive_module(self):
        self.client.force_login(self.admin)

        # Bei aktivem Modul vorhanden
        response = self.client.get("/suche/?q=Herbstturnier")
        self.assertContains(response, "<h2>Turniere</h2>")
        self.assertEqual(len(response.context["ergebnisse"]["turniere"]), 1)

        response = self.client.get("/suche/?q=Neuigkeiten")
        self.assertContains(response, "<h2>Ankündigungen</h2>")
        self.assertEqual(len(response.context["ergebnisse"]["news"]), 1)

        # Deaktivieren
        self.cfg.turniere_aktiv = False
        self.cfg.nachrichten_aktiv = False
        self.cfg.save()

        response = self.client.get("/suche/?q=Herbstturnier")
        self.assertEqual(len(response.context["ergebnisse"]["turniere"]), 0)
        self.assertNotContains(response, "<h2>Turniere</h2>")

        response = self.client.get("/suche/?q=Neuigkeiten")
        self.assertEqual(len(response.context["ergebnisse"]["news"]), 0)
        self.assertNotContains(response, "<h2>Ankündigungen</h2>")


class ModuleFinanzIntegritaetTests(TestCase):
    def setUp(self):
        self.admin = make_user("kassenwart", ADMIN_GROUP)
        self.member = Member.objects.create(
            vorname="Erika",
            nachname="Muster",
            status=Member.Status.AKTIV,
            eintrittsdatum=date(2026, 1, 1),
        )
        self.kategorie = FeeCategory.objects.create(name="Erwachsene")
        self.fee = MembershipFee.objects.create(
            member=self.member,
            jahr=2026,
            betrag=Decimal("60.00"),
            faellig_am=date(2026, 1, 31),
        )

    def test_zahlung_erzeugt_kasseneintrag_auch_wenn_kassenbuch_deaktiviert(self):
        """Finanzdaten werden nie verloren oder übersprungen (ADR-005, ADR-019)."""
        cfg = ModuleSettings.get_solo()
        cfg.kassenbuch_aktiv = False
        cfg.save()

        vorher_anzahl = CashEntry.objects.count()
        zahlung_erfassen(self.fee, betrag=Decimal("60.00"), benutzer=self.admin)
        nachher_anzahl = CashEntry.objects.count()

        self.assertEqual(nachher_anzahl, vorher_anzahl + 1)
        eintrag = CashEntry.objects.latest("pk")
        self.assertEqual(eintrag.betrag, Decimal("60.00"))
        self.assertEqual(eintrag.erfasst_von, self.admin)
