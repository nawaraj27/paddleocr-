from django.contrib import admin

from .models import Store, StoreMembership


class MembershipInline(admin.TabularInline):
    model = StoreMembership
    extra = 1


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "currency", "is_active", "created_at")
    list_filter = ("is_active", "currency")
    search_fields = ("name", "owner__username", "owner__email")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]


@admin.register(StoreMembership)
class StoreMembershipAdmin(admin.ModelAdmin):
    list_display = ("store", "user", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("store__name", "user__username")
