"""Review & Map workspace: turn pending OCR documents into ledger entries."""
from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from apps.inventory.models import Product
from apps.inventory.services import NegativeStockError
from .models import DocumentMapping, Transaction
from .services import ensure_mapping, post_document


def _store(request):
    return getattr(request, "store", None)


class MappingQueueView(LoginRequiredMixin, View):
    def get(self, request):
        store = _store(request)
        if store is None:
            return render(request, "ledger/queue.html", {"mappings": []})
        from apps.processing.models import ExtractedDocument
        docs = ExtractedDocument.objects.filter(
            uploaded_by=request.user, mapping__isnull=True)[:200]
        for d in docs:
            ensure_mapping(d, store)
        mappings = (DocumentMapping.objects.filter(store=store)
                    .select_related("document", "transaction")
                    .order_by("status", "-created_at")[:200])
        return render(request, "ledger/queue.html", {"mappings": mappings})


class MappingReviewView(LoginRequiredMixin, View):
    def get(self, request, pk):
        store = _store(request)
        mapping = get_object_or_404(DocumentMapping, pk=pk, store=store)
        raw = mapping.document.raw_json or {}
        products = list(Product.objects.filter(store=store, is_active=True)
                        .values("id", "name", "sku"))
        review_data = {
            "url": reverse("ledger:review", args=[mapping.id]),
            "queueUrl": reverse("ledger:queue"),
            "raw": raw,
            "items": raw.get("items", []),
            "products": products,
        }
        return render(request, "ledger/review.html", {
            "mapping": mapping,
            "doc": mapping.document,
            "review_data": review_data,
            "kinds": Transaction.Kind.choices,
        })

    def post(self, request, pk):
        store = _store(request)
        if store is None:
            return HttpResponseForbidden("No active store")
        mapping = get_object_or_404(DocumentMapping, pk=pk, store=store)
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "invalid json"}, status=400)

        if payload.get("action") == "reject":
            mapping.status = DocumentMapping.Status.REJECTED
            mapping.notes = str(payload.get("notes", ""))[:1000]
            mapping.save(update_fields=["status", "notes", "updated_at"])
            return JsonResponse({"status": "rejected"})

        try:
            txn = post_document(
                mapping, user=request.user,
                lines=payload.get("lines", []),
                kind=payload.get("kind", ""),
                party_name=payload.get("party_name", ""),
                number=payload.get("number", ""))
        except NegativeStockError as e:
            return JsonResponse({"detail": str(e)}, status=409)
        except Exception as e:  # noqa: BLE001
            return JsonResponse({"detail": f"posting failed: {e}"}, status=400)
        return JsonResponse({
            "status": "mapped", "transaction_id": txn.id,
            "kind": txn.kind, "number": txn.number})


class TransactionListView(LoginRequiredMixin, View):
    def get(self, request):
        store = _store(request)
        kind = request.GET.get("kind") or ""
        qs = (Transaction.objects.filter(store=store)
              .select_related("party").order_by("-date", "-id")
              if store else Transaction.objects.none())
        if kind:
            qs = qs.filter(kind=kind)
        return render(request, "ledger/transactions.html",
                      {"transactions": qs[:300], "kind": kind})
