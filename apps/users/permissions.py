"""Reusable DRF permission classes for RBAC."""
from rest_framework.permissions import BasePermission


class IsApproved(BasePermission):
    message = "Your account is awaiting admin approval."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_approved)


class _RoleRequired(BasePermission):
    roles: tuple = ()

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_approved and
                    (u.role in self.roles or u.is_superuser))


class IsAdmin(_RoleRequired):
    roles = ("admin",)
    message = "Admin role required."


class CanUpload(_RoleRequired):
    roles = ("admin", "manager", "analyst")
    message = "Upload permission required."


class CanViewAnalytics(_RoleRequired):
    roles = ("admin", "manager", "analyst")
    message = "Analytics permission required."
