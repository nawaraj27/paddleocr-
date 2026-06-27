from django.contrib import admin

from .models import (SiteSettings, FeatureBlock, Screenshot,
                     PlatformDownload, NavLink)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("brand_name", "hero_headline")


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
