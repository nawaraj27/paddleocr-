"""Admin-editable content powering the public landing page."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class SiteSettings(TimeStampedModel):
    """Singleton holding global brand + hero copy + service keys."""
    brand_name = models.CharField(max_length=80, default="Mero Dokan")
    hero_headline = models.CharField(max_length=160,
                                     default="Revenue-first analytics")
    hero_highlight = models.CharField(
        max_length=80, default="Revenue-first",
        help_text="Substring of the headline to highlight.")
    hero_subheadline = models.CharField(
        max_length=300,
        default="Turn receipts and bills into stock, sales and insight, fast.")
    social_proof_count = models.CharField(max_length=20, default="15,285")
    primary_cta_label = models.CharField(max_length=40, default="Get started")
    primary_cta_href = models.CharField(max_length=200, default="/auth/register/")

    # --- Service keys (never returned to frontend) ---
    gemini_api_key = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Gemini API key. Stored in DB; never exposed to frontend.")
    gemini_model = models.CharField(
        max_length=80, blank=True, default="",
        help_text="Override Gemini model name (leave blank to use env default).")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self) -> str:
        return self.brand_name

    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("Only one SiteSettings row is allowed.")
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        return cls.objects.first() or cls()


class FeatureBlock(TimeStampedModel):
    """Alternating split-grid marketing feature."""

    class Layout(models.TextChoices):
        LEFT = "left", "Image left"
        RIGHT = "right", "Image right"

    title = models.CharField(max_length=120)
    body = models.TextField()
    image = models.ImageField(upload_to="cms/features/", null=True, blank=True)
    layout = models.CharField(max_length=8, choices=Layout.choices,
                              default=Layout.RIGHT)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.title


class Screenshot(TimeStampedModel):
    class Chrome(models.TextChoices):
        BROWSER = "browser", "Browser"
        PHONE = "phone", "Phone"
        WINDOWS = "windows", "Windows"

    image = models.ImageField(upload_to="cms/screens/")
    caption = models.CharField(max_length=160, blank=True)
    chrome = models.CharField(max_length=10, choices=Chrome.choices,
                              default=Chrome.BROWSER)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.caption or f"Screenshot {self.pk}"


class PlatformDownload(TimeStampedModel):
    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"
        WEB = "web", "Web"
        WINDOWS = "windows", "Windows"

    platform = models.CharField(max_length=10, choices=Platform.choices)
    label = models.CharField(max_length=60)
    url = models.URLField()
    icon = models.CharField(max_length=40, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ("order", "id")

    def __str__(self) -> str:
        return f"{self.get_platform_display()} — {self.label}"


class NavLink(TimeStampedModel):
    class Group(models.TextChoices):
        NAV = "nav", "Top nav"
        FOOTER = "footer", "Footer"

    group = models.CharField(max_length=8, choices=Group.choices,
                             default=Group.NAV, db_index=True)
    section = models.CharField(max_length=40, blank=True,
                               help_text="Footer column heading.")
    label = models.CharField(max_length=60)
    href = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ("group", "order", "id")

    def __str__(self) -> str:
        return f"[{self.group}] {self.label}"
