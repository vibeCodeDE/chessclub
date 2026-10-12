import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Erstellt oder aktualisiert den initialen Superadmin aus Umgebungsvariablen."

    def handle(self, *args, **options):
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not password:
            self.stdout.write("Kein DJANGO_SUPERUSER_PASSWORD gesetzt – überspringe.")
            return

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com").strip()

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        from django.contrib.auth.models import Group
        admin_group, _ = Group.objects.get_or_create(name="admin")
        user.groups.add(admin_group)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Superadmin '{username}' erfolgreich erstellt."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Passwort für Superadmin '{username}' aktualisiert."))
