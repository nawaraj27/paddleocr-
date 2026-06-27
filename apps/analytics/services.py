"""Analytics aggregations over ExtractedDocument/InvoiceItem.

Queries are cached (per-user + filter signature) for ANALYTICS_CACHE_TTL to
keep the dashboard cheap. All heavy lifting is DB-side aggregation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum, Count, Avg, F, DecimalField
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

from apps.processing.models import ExtractedDocument, InvoiceItem


def _cache_key(user_id, filters) -> str:
    sig = hashlib.sha256(json.dumps(filters, sort_keys=True, default=str)
                         .encode()).hexdigest()[:16]
    return f"analytics:{user_id}:{sig}"


def _base_qs(user, filters):
    qs = ExtractedDocument.objects.filter(uploaded_by=user)
    if filters.get("saved_only", True):
        qs = qs.filter(is_saved=True)
    if filters.get("vendor"):
        qs = qs.filter(vendor_name__icontains=filters["vendor"])
    if filters.get("category"):
        qs = qs.filter(category_id=filters["category"])
    if filters.get("date_from"):
        qs = qs.filter(invoice_date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(invoice_date__lte=filters["date_to"])
    return qs


def compute(user, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    filters = filters or {}
    key = _cache_key(user.id, filters)
    cached = cache.get(key)
    if cached is not None:
        return cached

    qs = _base_qs(user, filters)
    dec = DecimalField(max_digits=16, decimal_places=2)

    totals = qs.aggregate(
        total_documents=Count("id"),
        total_revenue=Sum("total_amount", output_field=dec),
        avg_order_value=Avg("total_amount", output_field=dec),
    )

    grouping = filters.get("granularity", "day")
    trunc = {"day": TruncDay, "week": TruncWeek,
             "month": TruncMonth}.get(grouping, TruncDay)
    trend = list(
        qs.exclude(invoice_date__isnull=True)
        .annotate(period=trunc("invoice_date"))
        .values("period")
        .annotate(revenue=Sum("total_amount", output_field=dec),
                  count=Count("id"))
        .order_by("period"))

    vendors = list(
        qs.exclude(vendor_name="")
        .values("vendor_name")
        .annotate(revenue=Sum("total_amount", output_field=dec),
                  count=Count("id"))
        .order_by("-revenue")[:10])

    items_qs = InvoiceItem.objects.filter(document__in=qs)
    top_products = list(
        items_qs.values("name")
        .annotate(qty=Sum("quantity"), revenue=Sum("amount"),
                  freq=Count("id"))
        .order_by("-freq")[:10])

    categories = list(
        qs.values("category__name")
        .annotate(count=Count("id"),
                  revenue=Sum("total_amount", output_field=dec))
        .order_by("-count"))

    result = {
        "totals": {
            "total_documents": totals["total_documents"] or 0,
            "total_revenue": float(totals["total_revenue"] or 0),
            "avg_order_value": float(totals["avg_order_value"] or 0),
        },
        "trend": [
            {"period": t["period"].isoformat() if t["period"] else None,
             "revenue": float(t["revenue"] or 0), "count": t["count"]}
            for t in trend
        ],
        "vendors": [
            {"vendor": v["vendor_name"], "revenue": float(v["revenue"] or 0),
             "count": v["count"]} for v in vendors
        ],
        "top_products": [
            {"name": p["name"], "quantity": float(p["qty"] or 0),
             "revenue": float(p["revenue"] or 0), "frequency": p["freq"]}
            for p in top_products
        ],
        "categories": [
            {"category": c["category__name"] or "Uncategorized",
             "count": c["count"], "revenue": float(c["revenue"] or 0)}
            for c in categories
        ],
    }
    cache.set(key, result, settings.ANALYTICS_CACHE_TTL)
    return result
