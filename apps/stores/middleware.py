"""Workspace guards: login -> approval -> active-store resolution.

Runs after AuthenticationMiddleware. Public paths are skipped so the landing
page and auth views stay open; everything else requires an authenticated,
approved user who is a member of a resolved store.
"""
from __future__ import annotations

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from .models import Store, StoreMembership


def _is_public(path: str) -> bool:
    if path == "/":
        return True
    return path.startswith(("/auth/", "/admin/", "/static/", "/media/",
                            "/api/content/"))


class WorkspaceGuardMiddleware:
    """Single middleware enforcing login + approval + store membership."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if _is_public(path):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return redirect_to_login(path)
        if not getattr(user, "is_approved", False) and not user.is_superuser:
            return redirect("users:pending")

        store = self._resolve_store(request, user)
        if store is None:
            # No store yet -> allow the store-management pages, else send there.
            if path.startswith("/app/stores"):
                return self.get_response(request)
            return redirect("stores:select")
        request.store = store
        return self.get_response(request)

    def _resolve_store(self, request, user):
        sid = request.session.get("active_store_id")
        qs = Store.objects.filter(is_active=True)
        if user.is_superuser:
            return qs.filter(pk=sid).first() if sid else qs.first()
        member_stores = qs.filter(memberships__user=user,
                                  memberships__is_active=True)
        if sid:
            store = member_stores.filter(pk=sid).first()
            if store:
                return store
        return member_stores.first()
