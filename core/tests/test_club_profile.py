from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog, ClubProfile
from core.roles import ADMIN_GROUP, KAPITAEN_GROUP, MITGLIED_GROUP


class ClubProfileModelTests(TestCase):
    def test_get_solo_returns_singleton(self):
        """get_solo liefert das Singleton mit pk=1."""
        profil = ClubProfile.get_solo()
        self.assertEqual(profil.pk, 1)

    def test_save_enforces_singleton_pk_1(self):
        """Egal welche PK vergeben wird, der Datensatz behält pk=1."""
        profil = ClubProfile(pk=99, name="Test Schachklub e.V.")
        profil.save()
        self.assertEqual(profil.pk, 1)
        self.assertEqual(ClubProfile.objects.count(), 1)
        self.assertEqual(ClubProfile.get_solo().name, "Test Schachklub e.V.")

    def test_delete_is_prevented(self):
        """Löschen des Singleton-Datensatzes wird unterbunden."""
        profil = ClubProfile.get_solo()
        profil.delete()
        self.assertEqual(ClubProfile.objects.count(), 1)


class ClubProfileViewAndPermissionsTests(TestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
        self.kapitaen_group, _ = Group.objects.get_or_create(name=KAPITAEN_GROUP)
        self.mitglied_group, _ = Group.objects.get_or_create(name=MITGLIED_GROUP)

        self.admin_user = User.objects.create_user("admin", "admin@example.com", "pass")
        self.admin_user.groups.add(self.admin_group)

        self.kapitaen_user = User.objects.create_user("kapitaen", "kapi@example.com", "pass")
        self.kapitaen_user.groups.add(self.kapitaen_group)

        self.mitglied_user = User.objects.create_user("mitglied", "mitg@example.com", "pass")
        self.mitglied_user.groups.add(self.mitglied_group)

    def test_admin_can_access_and_update_club_profile(self):
        """Admin kann die Profilmaske aufrufen und speichern; AuditLog wird erfasst."""
        self.client.force_login(self.admin_user)
        url = reverse("core:club_setup_profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = {
            "name": "Schachfreunde 1920 e.V.",
            "kurzname": "SF 1920",
            "kontakt_email": "info@sf1920.de",
            "gruendungsjahr": "1920",
            "ort": "Freiburg",
            "spiellokal": "Vereinsheim Hauptstr. 1",
            "spielabend_zeiten": "Freitags ab 19:30 Uhr",
            "jugend_zeiten": "Freitags 17:30 - 19:00 Uhr",
            "beschreibung": "Traditioneller Schachverein",
            "sepa_glaeubiger_id": "DE12ZZZ00000000001",
            "sepa_glaeubiger_name": "Schachfreunde 1920 e.V.",
            "sepa_iban": "DE89370400440532013000",
            "sepa_bic": "GENODED1PAU",
        }
        post_response = self.client.post(url, data)
        self.assertRedirects(post_response, url)

        profil = ClubProfile.get_solo()
        self.assertEqual(profil.name, "Schachfreunde 1920 e.V.")
        self.assertEqual(profil.kurzname, "SF 1920")
        self.assertEqual(profil.ort, "Freiburg")

        # Prüfen, dass AuditLog geschrieben wurde
        self.assertTrue(
            AuditLog.objects.filter(aktion="Vereinsprofil aktualisiert", benutzer=self.admin_user).exists()
        )

    def test_context_processor_reflects_db_profile(self):
        """Das Template-System erhält die Daten aus dem Datenbank-Profil."""
        profil = ClubProfile.get_solo()
        profil.name = "Echter Schachverein 2026 e.V."
        profil.kurzname = "ESV 2026"
        profil.save()

        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ESV 2026")

    def test_non_admins_forbidden_negative_tests(self):
        """Negativtests: Gast, Mitglied und Kapitän erhalten keinen Zugriff auf Setup-Routen."""
        url = reverse("core:club_setup_profile")

        # 1. Gast (nicht eingeloggt) -> Redirect zum Login
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        # 2. Rolle Mitglied -> 403 Forbidden
        self.client.force_login(self.mitglied_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        post_resp = self.client.post(url, {"name": "Gehackt"})
        self.assertEqual(post_resp.status_code, 403)

        # 3. Rolle Kapitän -> 403 Forbidden
        self.client.force_login(self.kapitaen_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
