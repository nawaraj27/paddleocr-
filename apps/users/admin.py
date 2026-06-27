from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_approved", "is_active",
                    "created_at")
    list_filter = ("role", "is_approved", "is_active")
    actions = ["approve_users"]
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Workflow", {"fields": ("role", "is_approved", "approved_at",
                                 "approved_by", "email_verified")}),
    )

    @admin.action(description="Approve & activate selected users")
    def approve_users(self, request, queryset):
        for u in queryset:
            u.approve(by=request.user)
        self.message_user(request, f"Approved {queryset.count()} users.")
