"""Management command: create a superuser from env vars if none exists.

Environment variables:
    SUPERUSER_USERNAME   (required) username for the superuser account
    SUPERUSER_EMAIL      (required) email address for the superuser account
    SUPERUSER_PASSWORD   (required) password for the superuser account

Falls back to safe defaults so the command never hangs waiting for input.
Run automatically on Railway deploy via railway.json startCommand.
Idempotent — safe to run on every deploy.
"""
import os
import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser from env vars if none exists. Fully non-interactive."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get("SUPERUSER_USERNAME", "admin")
        email = os.environ.get("SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get("SUPERUSER_PASSWORD", "Admin1234!demo")

        try:
            # If a superuser with this username already exists, update
            # email/password and ensure the account is active — then exit cleanly.
            try:
                user = User.objects.get(username=username)
                if not user.is_superuser:
                    user.is_superuser = True
                    user.is_staff = True
                user.email = email
                user.set_password(password)
                user.is_approved = True
                user.is_active = True
                user.role = User.Role.ADMIN
                user.save(update_fields=[
                    "email", "password", "is_superuser", "is_staff",
                    "is_approved", "is_active", "role", "updated_at",
                ])
                self.stdout.write(self.style.SUCCESS(
                    f"Superuser already exists — updated: username='{username}' "
                    f"email='{email}'"))
                self.stdout.flush()
                return
            except User.DoesNotExist:
                pass

            # No matching user found — create one from scratch.
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )

            # Re-fetch and explicitly set custom fields so they are guaranteed
            # to be persisted regardless of any manager-level defaults.
            user = User.objects.get(username=username)
            user.role = User.Role.ADMIN
            user.is_approved = True
            user.is_active = True
            user.save(update_fields=["role", "is_approved", "is_active", "updated_at"])

            self.stdout.write(self.style.SUCCESS(
                f"Superuser created: username='{username}' email='{email}'"))
            self.stdout.flush()

        except Exception as exc:  # noqa: BLE001
            self.stderr.write(self.style.ERROR(
                f"Failed to create superuser: {exc}"))
            self.stderr.flush()
            sys.exit(1)
