"""Custom user with roles + admin-approval workflow."""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel
from .managers import UserManager


class User(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        ANALYST = "analyst", "Analyst"
        VIEWER = "viewer", "Viewer"

    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=16, choices=Role.choices,
                            default=Role.VIEWER, db_index=True)
    is_approved = models.BooleanField(default=False, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="approved_users")
    email_verified = models.BooleanField(default=False)
    failed_login_count = models.PositiveIntegerField(default=0)

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta(TimeStampedModel.Meta):
        pass

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"

    # -- RBAC helpers --------------------------------------------------
    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    def can_manage_users(self) -> bool:
        return self.is_admin_role

    def can_upload(self) -> bool:
        return self.role in (self.Role.ADMIN, self.Role.MANAGER, self.Role.ANALYST)

    def can_view_analytics(self) -> bool:
        return self.role in (self.Role.ADMIN, self.Role.MANAGER, self.Role.ANALYST)

    def approve(self, by, role=None):
        from django.utils import timezone
        self.is_approved = True
        self.is_active = True
        self.approved_at = timezone.now()
        self.approved_by = by
        if role:
            self.role = role
        self.save(update_fields=["is_approved", "is_active", "approved_at",
                                 "approved_by", "role", "updated_at"])
