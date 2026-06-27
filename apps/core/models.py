"""Shared base models: timestamps, categories and the audit trail."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base giving every record created_at / updated_at."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)


class Category(TimeStampedModel):
    """User-defined grouping for extracted documents (e.g. 'Utilities')."""
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    color = models.CharField(max_length=9, default="#D4E4B4")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="categories")

    class Meta(TimeStampedModel.Meta):
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.name) or "category"
            slug, i = base, 1
            while Category.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)


class AuditLog(TimeStampedModel):
    """Append-only record of security-relevant actions."""

    class Action(models.TextChoices):
        LOGIN = "login", "Login"
        LOGIN_FAILED = "login_failed", "Login failed"
        LOGOUT = "logout", "Logout"
        REGISTER = "register", "Register"
        UPLOAD = "upload", "Upload"
        DATA_ACCESS = "data_access", "Data access"
        EXPORT = "export", "Export"
        ADMIN_ACTION = "admin_action", "Admin action"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_logs")
    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    target = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["action", "created_at"])]

    def __str__(self) -> str:
        who = self.actor or "anonymous"
        return f"{who} {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"

    @classmethod
    def record_safe(cls, actor, action, target="", **metadata):
        """Record an audit entry from a known user (no request object)."""
        if actor is not None and not getattr(actor, "is_authenticated", False):
            actor = None
        return cls.objects.create(
            actor=actor, action=action, target=str(target)[:255],
            metadata=metadata or {})

    @classmethod
    def record(cls, request, action, target="", **metadata):
        actor = getattr(request, "user", None)
        if actor is not None and not getattr(actor, "is_authenticated", False):
            actor = None
        return cls.objects.create(
            actor=actor, action=action, target=str(target)[:255],
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
            metadata=metadata or {})


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
