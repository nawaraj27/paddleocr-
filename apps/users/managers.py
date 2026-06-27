from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, username, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra):
        extra.setdefault("role", "viewer")
        extra.setdefault("is_approved", False)
        extra.setdefault("is_active", False)   # inactive until admin approves
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(username, email, password, **extra)

    def create_superuser(self, username, email, password=None, **extra):
        extra.update(role="admin", is_approved=True, is_active=True,
                     is_staff=True, is_superuser=True)
        return self._create(username, email, password, **extra)
