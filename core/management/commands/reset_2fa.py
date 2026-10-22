from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import AuditLog, TwoFactorDevice

User = get_user_model()


class Command(BaseCommand):
    help = "Setzt das Zwei-Faktor-Authentifizierungsgerät (2FA) eines Benutzers per Notfall-CLI zurück."

    def add_arguments(self, parser):
        parser.add_argument(
            "username",
            type=str,
            help="Benutzername des Kontos, dessen 2FA-Gerät gelöscht werden soll.",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        user = User.objects.filter(username=username).first()

        if not user:
            raise CommandError(f"Benutzer '{username}' existiert nicht.")

        device = TwoFactorDevice.objects.filter(user=user).first()
        if not device:
            raise CommandError(f"Benutzer '{username}' hat kein 2FA-Gerät eingerichtet.")

        with transaction.atomic():
            device.delete()
            AuditLog.objects.create(
                benutzer=user,
                aktion="2FA via CLI zurückgesetzt",
                text=f"2FA für Benutzer '{username}' per Management-Command zurückgesetzt.",
            )

        self.stdout.write(
            self.style.SUCCESS(f"2FA für Benutzer '{username}' erfolgreich zurückgesetzt.")
        )
