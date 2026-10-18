"""Tests für Rate-Limiting mit django-ratelimit.

Gemäß PRD N1.1 (kein Google reCAPTCHA / keine externen Tracker/CDNs),
N1.6 (Missbrauchsschutz) und ADR-028.
"""

from datetime import date, timedelta
from django.conf import settings
from django.core.cache import caches
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from core.models import StaffInvitation
from dues.models import FeeCategory
from tournaments.models import Tournament


class RatelimitConfigTests(TestCase):
    """Prüft die Grundeinstellungen des Rate-Limitings."""

    def test_ratelimit_in_test_settings_standardmaessig_deaktiviert(self):
        """In Testumgebungen ist RATELIMIT_ENABLE standardmäßig False,
        damit reguläre Tests nicht versehentlich gedrosselt werden."""
        self.assertFalse(settings.RATELIMIT_ENABLE)


@override_settings(RATELIMIT_ENABLE=True)
class RatelimitEndpointsTests(TestCase):
    """Prüft das Rate-Limiting auf allen geschützten öffentlichen Endpunkten."""

    def setUp(self):
        # Cache vor jedem Test leeren, um saubere Zähler zu garantieren
        caches["default"].clear()
        self.client = Client()

    def tearDown(self):
        caches["default"].clear()

    def test_join_info_get_wird_nicht_limitiert(self):
        """GET-Anfragen an die Beitrittsseite werden nicht gezählt oder gedrosselt."""
        for _ in range(10):
            response = self.client.get("/mitglied-werden/")
            self.assertEqual(response.status_code, 200)

    def test_join_info_post_wird_nach_limit_abgewiesen_negativtest(self):
        """Negativtest: Mehr als 5 POST-Anfragen pro Minute an /mitglied-werden/
        werden mit HTTP 429 (Too Many Requests) abgewiesen."""
        FeeCategory.objects.create(name="Erwachsene", aktiv=True)
        form_data = {
            "name": "Interessent",
            "email": "interessent@example.org",
            "interesse": "erwachsene",
            "nachricht": "Ich möchte schnuppern.",
        }

        # 5 erlaubte Versuche
        for i in range(5):
            res = self.client.post("/mitglied-werden/", form_data)
            self.assertIn(res.status_code, [200, 302], f"Versuch {i+1} sollte erlaubt sein")

        # 6. Versuch wird mit HTTP 429 blockiert
        res_blocked = self.client.post("/mitglied-werden/", form_data)
        self.assertEqual(res_blocked.status_code, 429)
        self.assertEqual(res_blocked["Retry-After"], "60")
        self.assertTemplateUsed(res_blocked, "core/ratelimited.html")
        self.assertContains(res_blocked, "Zu viele Anfragen", status_code=429)
        self.assertContains(res_blocked, "Anfragelimit vorübergehend erreicht", status_code=429)

        # GET-Anfrage bleibt danach weiterhin voll erreichbar (nicht blockiert)
        res_get = self.client.get("/mitglied-werden/")
        self.assertEqual(res_get.status_code, 200)

    def test_turnier_anmeldung_post_wird_gedrosselt_negativtest(self):
        """Negativtest: Öffentliche Turnieranmeldungen werden nach 5 POSTs pro Minute gedrosselt."""
        turnier = Tournament.objects.create(
            name="Offene Vereinsmeisterschaft",
            datum=timezone.localdate() + timedelta(days=14),
            anmeldeschluss=timezone.localdate() + timedelta(days=7),
            oeffentlich=True,
            status=Tournament.Status.ANMELDUNG,
        )
        post_data = {
            "name": "Gastspieler",
            "email": "gast@example.org",
            "verein": "SV Nachbarort",
        }

        # 5 Versuche innerhalb des Limits
        for i in range(5):
            res = self.client.post(f"/turniere/{turnier.pk}/", post_data)
            self.assertIn(res.status_code, [200, 302], f"Versuch {i+1} sollte durchgehen")

        # 6. Versuch wird mit 429 abgewiesen
        res_blocked = self.client.post(f"/turniere/{turnier.pk}/", post_data)
        self.assertEqual(res_blocked.status_code, 429)
        self.assertEqual(res_blocked["Retry-After"], "60")
        self.assertContains(res_blocked, "Zu viele Anfragen", status_code=429)

        # GET auf das Turnier bleibt uneingeschränkt möglich
        res_get = self.client.get(f"/turniere/{turnier.pk}/")
        self.assertEqual(res_get.status_code, 200)

    def test_passwort_reset_post_wird_gedrosselt_negativtest(self):
        """Negativtest: Passwort-Reset-POST-Anfragen werden nach 5 Versuchen mit HTTP 429 gedrosselt."""
        post_data = {"email": "mitglied@example.org"}

        for i in range(5):
            res = self.client.post("/passwort/aendern/", post_data)
            self.assertIn(res.status_code, [200, 302], f"Versuch {i+1} sollte erlaubt sein")

        res_blocked = self.client.post("/passwort/aendern/", post_data)
        self.assertEqual(res_blocked.status_code, 429)
        self.assertEqual(res_blocked["Retry-After"], "60")
        self.assertContains(res_blocked, "Zu viele Anfragen", status_code=429)

    def test_einladung_post_wird_gedrosselt_negativtest(self):
        """Negativtest: POST-Versuche auf Einladungslinks werden nach 5 Versuchen mit HTTP 429 gedrosselt."""
        from django.contrib.auth.models import User
        admin_user = User.objects.create_superuser("admin_inv", "admin@example.org", "pass")
        invitation = StaffInvitation.objects.create(
            email="funktionaer@example.org",
            vorname="Max",
            nachname="Muster",
            rolle="admin",
            token="test-token-12345",
            gueltig_bis=timezone.now() + timedelta(days=7),
            status="offen",
            eingeladen_von=admin_user,
        )
        post_data = {
            "username": "neuer_vorstand",
            "password": "SicheresPasswort123!",
            "password_confirm": "SicheresPasswort123!",
        }

        for i in range(5):
            res = self.client.post(f"/einladung/{invitation.token}/", post_data)
            # Kann 200 (Formfehler/Validierung) oder 302 sein
            self.assertIn(res.status_code, [200, 302], f"Versuch {i+1} sollte erlaubt sein")

        res_blocked = self.client.post(f"/einladung/{invitation.token}/", post_data)
        self.assertEqual(res_blocked.status_code, 429)
        self.assertEqual(res_blocked["Retry-After"], "60")
        self.assertContains(res_blocked, "Zu viele Anfragen", status_code=429)

    def test_ratelimit_ajax_oder_json_liefert_json_response(self):
        """Wenn eine blockierte Anfrage per AJAX/JSON gestellt wird, erfolgt eine JSON-Antwort mit 429."""
        FeeCategory.objects.create(name="Erwachsene", aktiv=True)
        form_data = {
            "name": "SpamBot",
            "email": "bot@example.org",
            "interesse": "erwachsene",
        }
        for _ in range(5):
            self.client.post("/mitglied-werden/", form_data)

        # 6. Versuch als AJAX-Request
        res = self.client.post(
            "/mitglied-werden/",
            form_data,
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res["Retry-After"], "60")
        data = res.json()
        self.assertIn("detail", data)
        self.assertIn("Zu viele Anfragen", data["detail"])

    def test_getrennte_ip_adressen_haben_getrennte_budgets(self):
        """Anfragen von IP A drosseln nicht Anfragen von IP B."""
        FeeCategory.objects.create(name="Erwachsene", aktiv=True)
        form_data = {
            "name": "Tester",
            "email": "test@example.org",
            "interesse": "erwachsene",
        }

        # IP 1 erreicht das Limit
        for _ in range(5):
            self.client.post("/mitglied-werden/", form_data, REMOTE_ADDR="192.168.1.10")
        blocked_ip1 = self.client.post("/mitglied-werden/", form_data, REMOTE_ADDR="192.168.1.10")
        self.assertEqual(blocked_ip1.status_code, 429)

        # IP 2 hat frisches Kontingent und wird nicht blockiert
        ok_ip2 = self.client.post("/mitglied-werden/", form_data, REMOTE_ADDR="192.168.1.20")
        self.assertIn(ok_ip2.status_code, [200, 302])
