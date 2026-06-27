"""Strict invoice schema + validation/normalization.

The schema is the single source of truth shared by the Gemini prompt and the
post-response validator. No free-text is accepted: the model is constrained to
emit exactly this JSON object, which we then validate and coerce before storage.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Field name -> (type, required). Kept tiny to minimize prompt tokens.
INVOICE_FIELDS = {
    "doc_type": ("string", False),
    "party_name": ("string", False),
    "invoice_number": ("string", False),
    "vendor_name": ("string", False),
    "date": ("date", False),
    "currency": ("string", False),
    "subtotal": ("number", False),
    "tax": ("number", False),
    "total_amount": ("number", False),
    "items": ("items", False),
}

# Minimal JSON shape sent to Gemini as a response schema (token-frugal).
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type": {"type": "string", "enum": ["sale", "purchase", "estimate"]},
        "party_name": {"type": "string"},
        "invoice_number": {"type": "string"},
        "vendor_name": {"type": "string"},
        "date": {"type": "string"},
        "currency": {"type": "string"},
        "subtotal": {"type": "number"},
        "tax": {"type": "number"},
        "total_amount": {"type": "number"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "amount": {"type": "number"},
                },
            },
        },
    },
}


class SchemaError(ValueError):
    pass


@dataclass
class ValidatedInvoice:
    data: dict[str, Any]
    items: list[dict[str, Any]]
    confidence: float = 0.0


def _num(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("$", "").strip()
    import re
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else None


def _date(v):
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y",
                "%d %b %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s  # keep raw if unparseable; never crash


def validate(raw: dict) -> ValidatedInvoice:
    """Validate + coerce a model response into a storable invoice."""
    if not isinstance(raw, dict):
        raise SchemaError("response is not an object")

    out: dict[str, Any] = {}
    out["invoice_number"] = (str(raw.get("invoice_number")).strip()
                             if raw.get("invoice_number") else None)
    out["vendor_name"] = (str(raw.get("vendor_name")).strip()
                          if raw.get("vendor_name") else None)
    _dt = str(raw.get("doc_type") or "").strip().lower()
    out["doc_type"] = _dt if _dt in ("sale", "purchase", "estimate") else None
    out["party_name"] = (str(raw.get("party_name")).strip()
                         if raw.get("party_name") else None)
    out["date"] = _date(raw.get("date"))
    out["currency"] = (str(raw.get("currency")).strip()[:8]
                       if raw.get("currency") else None)
    out["subtotal"] = _num(raw.get("subtotal"))
    out["tax"] = _num(raw.get("tax"))
    out["total_amount"] = _num(raw.get("total_amount"))

    items = []
    for it in (raw.get("items") or []):
        if not isinstance(it, dict):
            continue
        items.append({
            "name": (str(it.get("name")).strip() if it.get("name") else ""),
            "quantity": _num(it.get("quantity")) or 0,
            "unit_price": _num(it.get("unit_price")),
            "amount": _num(it.get("amount")),
        })
    out["items"] = items

    # derive total if missing
    if out["total_amount"] is None and items:
        s = sum((i["amount"] or 0) for i in items)
        if s:
            out["total_amount"] = s

    conf = float(raw.get("_confidence", 0.0) or 0.0)
    return ValidatedInvoice(data=out, items=items, confidence=conf)
