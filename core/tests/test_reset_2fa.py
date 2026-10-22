"""Tests für den Notfall-CLI-Befehl reset_2fa (Aussperrschutz, T38)."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.models import AuditLog, TwoFactorDevice

User = get_user_model()


class Reset2FATests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("vorstand_user", password="secretpassword")

    def test_erfolgreicher_reset_loescht_geraet_und_schreibt_audit_log(self):
        """Erfolgreicher Notfall-Reset löscht das TOTP-Gerät und protokolliert die CLI-Aktion."""
        TwoFactorDevice.objects.create(
            user=self.user,
            secret="JBSWY3DPEHPK3PXP",
            bestaetigt=True,
        )
        self.assertTrue(TwoFactorDevice.objects.filter(user=self.user).exists())

        out = StringIO()
        call_command("reset_2fa", "vorstand_user", stdout=out)

        self.assertIn("2FA für Benutzer 'vorstand_user' erfolgreich zurückgesetzt.", out.getvalue())
        self.assertFalse(TwoFactorDevice.objects.filter(user=self.user).exists())

        log = AuditLog.objects.filter(
            benutzer=self.user,
            aktion="2FA via CLI zurückgesetzt",
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("vorstand_user", log.text)

    def test_reset_unbestaetigtes_geraet(self):
        """Auch ein unbestätigtes Gerät (z. B. abgebrochenes Setup) lässt sich bereinigen."""
        TwoFactorDevice.objects.create(
            user=self.user,
            secret="JBSWY3DPEHPK3PXP",
            bestaetigt=False,
        )
        out = StringIO()
        call_command("reset_2fa", "vorstand_user", stdout=out)
        self.assertFalse(TwoFactorDevice.objects.filter(user=self.user).exists())

    def test_nicht_existierender_benutzer_wirft_command_error_negativtest(self):
        """Negativtest: Ein nicht existierender Benutzername wird mit CommandError abgewiesen."""
        with self.assertRaises(CommandError) as ctx:
            call_command("reset_2fa", "unbekannter_nutzer")
        self.assertIn("existiert nicht", str(ctx.exception))

    def test_benutzer_ohne_2fa_wirft_command_error_negativtest(self):
        """Negativtest: Hat der Benutzer kein 2FA-Gerät, wird dies klar als CommandError gemeldet."""
        self.assertFalse(TwoFactorDevice.objects.filter(user=self.user).exists())
        with self.assertRaises(CommandError) as ctx:
            call_command("reset_2fa", "vorstand_user")
        self.assertIn("kein 2FA-Gerät eingerichtet", str(ctx.exception))
