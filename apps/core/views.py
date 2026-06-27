"""Public landing + authenticated dashboard shell."""
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class LandingView(TemplateView):
    template_name = "landing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["social_proof_count"] = "15,285"
        return ctx


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        from apps.processing.models import ExtractedDocument
        from apps.uploads.models import UploadedFile
        ctx = super().get_context_data(**kwargs)
        qs = ExtractedDocument.objects.filter(uploaded_by=self.request.user)
        ctx["total_documents"] = qs.count()
        ctx["recent"] = qs.select_related("category")[:8]
        ctx["pending_files"] = UploadedFile.objects.filter(
            uploaded_by=self.request.user,
            status__in=["pending", "processing"]).count()
        return ctx
