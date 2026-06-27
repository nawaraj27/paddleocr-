"""Lightweight audit middleware: attaches a request id; logs admin mutations."""
from __future__ import annotations

import uuid


class AuditLogMiddleware:
    SENSITIVE_PREFIXES = ("/admin/",)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = uuid.uuid4().hex[:12]
        response = self.get_response(request)
        try:
            self._maybe_log(request, response)
        except Exception:
            pass  # auditing must never break the request
        return response

    def _maybe_log(self, request, response):
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and \
                request.path.startswith(self.SENSITIVE_PREFIXES) and \
                getattr(request, "user", None) and request.user.is_authenticated:
            from .models import AuditLog
            AuditLog.record(request, AuditLog.Action.ADMIN_ACTION,
                            target=request.path, method=request.method,
                            status=response.status_code)
