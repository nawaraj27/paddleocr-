from django.contrib import admin
from .models import Category, AuditLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color", "created_by", "created_at")
    search_fields = ("name",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target", "ip_address")
    list_filter = ("action", "created_at")
    search_fields = ("target", "actor__username")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False
