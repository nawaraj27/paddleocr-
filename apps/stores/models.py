"""Multi-tenant store (Dokan) ownership and membership."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Store(TimeStampedModel):
    """A single dokan. A user may own several (User 1:M Store)."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="owned_stores", db_index=True)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    currency = models.CharField(max_length=8, default="NPR")
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    logo = models.ImageField(upload_to="store_logos/", null=True, blank=True)
    allow_negative_stock = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["owner", "is_active"])]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "store"
            slug, i = base, 1
            while Store.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)


class StoreMembership(TimeStampedModel):
    """Per-store role for staff (separate from platform-level User.role)."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        STAFF = "staff", "Staff"
        VIEWER = "viewer", "Viewer"

    store = models.ForeignKey(Store, on_delete=models.CASCADE,
                              related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="store_memberships")
    role = models.CharField(max_length=16, choices=Role.choices,
                            default=Role.STAFF)
    is_active = models.BooleanField(default=True)

    class Meta(TimeStampedModel.Meta):
        constraints = [models.UniqueConstraint(fields=["store", "user"],
                                               name="uniq_store_member")]

    def __str__(self) -> str:
        return f"{self.user} @ {self.store} ({self.role})"

    @property
    def can_write(self) -> bool:
        return self.role in (self.Role.OWNER, self.Role.MANAGER, self.Role.STAFF)
