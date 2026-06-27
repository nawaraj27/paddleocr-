"""DRF permissions for store-scoped access (compose with users.permissions)."""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from .models import StoreMembership


class IsStoreMember(BasePermission):
    message = "You are not a member of this store."

    def has_permission(self, request, view):
        store = getattr(request, "store", None)
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        if store is None:
            return False
        return StoreMembership.objects.filter(
            store=store, user=user, is_active=True).exists()


class HasStoreWriteRole(IsStoreMember):
    message = "You lack write permission in this store."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        user = request.user
        store = getattr(request, "store", None)
        if user.is_superuser:
            return True
        m = StoreMembership.objects.filter(
            store=store, user=user, is_active=True).first()
        return bool(m and m.can_write)
