"""HTML data viewer + export endpoints."""
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView

from apps.core.models import AuditLog, Category
from .models import ExtractedDocument
from .exporters import export_documents, CONTENT_TYPES


class DataViewerView(LoginRequiredMixin, TemplateView):
    template_name = "data/viewer.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = (ExtractedDocument.objects.filter(uploaded_by=self.request.user)
              .select_related("category").prefetch_related("items"))
        ctx["documents"] = qs[:200]
        ctx["categories"] = Category.objects.order_by("name")
        return ctx
def _queue_processing(file_id):
    from apps.processing.tasks import process_file

    print("QUEUE", file_id)

    try:
        result = process_file.delay(file_id)
        print("DELAY RETURNED", result)
    except Exception as e:
        print("DELAY ERROR", e)
        process_file(file_id)

class ExportView(LoginRequiredMixin, View):
    """Export filtered documents as csv | xlsx | json."""

    def get(self, request, fmt):
        if fmt not in CONTENT_TYPES:
            raise Http404("unknown format")
        qs = ExtractedDocument.objects.filter(
            uploaded_by=request.user).prefetch_related("items")
        # filters
        if request.GET.get("vendor"):
            qs = qs.filter(vendor_name__icontains=request.GET["vendor"])
        if request.GET.get("category"):
            qs = qs.filter(category_id=request.GET["category"])
        if request.GET.get("status"):
            qs = qs.filter(status=request.GET["status"])
        if request.GET.get("date_from"):
            qs = qs.filter(invoice_date__gte=request.GET["date_from"])
        if request.GET.get("date_to"):
            qs = qs.filter(invoice_date__lte=request.GET["date_to"])
        if request.GET.get("saved_only") == "1":
            qs = qs.filter(is_saved=True)

        payload, filename = export_documents(list(qs), fmt)
        AuditLog.record(request, AuditLog.Action.EXPORT, target=fmt,
                        count=qs.count())
        resp = HttpResponse(payload, content_type=CONTENT_TYPES[fmt])
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
