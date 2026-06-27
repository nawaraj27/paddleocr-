"""Persistence service: turn a validated invoice into relational records."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.utils import timezone

from apps.uploads.models import Status
from .models import ExtractedDocument, InvoiceItem
from .schema import ValidatedInvoice


def _dec(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def persist_extraction(uploaded_file, validated: ValidatedInvoice,
                       model_version: str, category=None,
                       is_saved: bool = False) -> ExtractedDocument:
    d = validated.data
    doc, _ = ExtractedDocument.objects.update_or_create(
        uploaded_file=uploaded_file,
        defaults=dict(
            uploaded_by=uploaded_file.uploaded_by,
            category=category,
            status=Status.COMPLETED,
            raw_json=d,
            invoice_number=(d.get("invoice_number") or "")[:120],
            vendor_name=(d.get("vendor_name") or "")[:200],
            invoice_date=d.get("date") if _is_iso_date(d.get("date")) else None,
            currency=(d.get("currency") or "")[:8],
            subtotal=_dec(d.get("subtotal")),
            tax=_dec(d.get("tax")),
            total_amount=_dec(d.get("total_amount")),
            model_version=model_version,
            confidence=validated.confidence,
            is_saved=is_saved,
            processed_at=timezone.now(),
        ),
    )
    doc.items.all().delete()
    InvoiceItem.objects.bulk_create([
        InvoiceItem(document=doc, name=(it.get("name") or "")[:255],
                    quantity=_dec(it.get("quantity")) or 0,
                    unit_price=_dec(it.get("unit_price")),
                    amount=_dec(it.get("amount")))
        for it in validated.items
    ])
    return doc


def _is_iso_date(v) -> bool:
    if not v:
        return False
    import re
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)))
