from django.contrib import admin
from django.utils.html import format_html

from .models import (SiteSettings, FeatureBlock, Screenshot,
                     PlatformDownload, NavLink)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("brand_name", "hero_headline", "gemini_key_status")
    readonly_fields = ("gemini_key_status",)
    fieldsets = (
        ("Branding", {"fields": (
            "brand_name", "hero_headline", "hero_highlight",
            "hero_subheadline", "social_proof_count",
            "primary_cta_label", "primary_cta_href")}),
        ("Gemini API", {"fields": (
            "gemini_api_key", "gemini_model", "gemini_key_status"),
            "description": "API key is stored securely. It is never returned to the frontend."}),
    )

    def gemini_key_status(self, obj):
        if obj.gemini_api_key:
            masked = obj.gemini_api_key[:6] + "••••••••" + obj.gemini_api_key[-4:]
            return format_html('<span style="color:green">✓ Configured ({})</span>', masked)
        return format_html('<span style="color:red">✗ Not set — falling back to env var</span>')
    gemini_key_status.short_description = "Key status"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Invalidate cache immediately after saving so next request picks up new key
        from apps.core.services.settings_service import invalidate_gemini_cache
        invalidate_gemini_cache()


@admin.register(FeatureBlock)
class FeatureBlockAdmin(admin.ModelAdmin):
    list_display = ("title", "layout", "order", "is_published")
    list_editable = ("layout", "order", "is_published")


@admin.register(Screenshot)
class ScreenshotAdmin(admin.ModelAdmin):
    list_display = ("caption", "chrome", "order", "is_published")
    list_editable = ("chrome", "order", "is_published")


@admin.register(PlatformDownload)
class PlatformDownloadAdmin(admin.ModelAdmin):
    list_display = ("platform", "label", "url", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(NavLink)
class NavLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "group", "section", "order", "is_active")
    list_editable = ("group", "section", "order", "is_active")
