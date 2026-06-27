"""Management command: create a superuser from env vars if none exists.

Environment variables (all optional — falls back to safe defaults):
    SUPERUSER_USERNAME   default: admin
    SUPERUSER_EMAIL      default: admin@example.com
    SUPERUSER_PASSWORD   default: Admin1234!demo

Run automatically on Railway deploy via railway.json startCommand.
Idempotent — safe to run on every deploy.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser from env vars if no superuser exists."

    def handle(self, *args, **options):
        User = get_user_model()

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS(
                "Superuser already exists — skipping creation."))
            return

        username = os.environ.get("SUPERUSER_USERNAME", "admin")
        email = os.environ.get("SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get("SUPERUSER_PASSWORD", "Admin1234!demo")

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        # Also mark as approved + admin role so they can log in immediately
        user.is_approved = True
        user.is_active = True
        user.role = User.Role.ADMIN
        user.save(update_fields=["is_approved", "is_active", "role"])

        self.stdout.write(self.style.SUCCESS(
            f"Superuser created: username='{username}' email='{email}' "
            f"(set SUPERUSER_PASSWORD env var to change the password)"))
