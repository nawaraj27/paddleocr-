"""Map a Gemini-extracted document into the operational ledger + inventory.

Design notes (enterprise):
* Human-in-the-loop: detection/classification is automatic, but the actual
  posting that mutates stock is an explicit confirm carrying reviewed lines.
* Atomic: the whole post (transaction + lines + stock movements + mapping) runs
  in one DB transaction; any error rolls everything back.
* Idempotent: keyed on the document's OneToOne DocumentMapping; a second confirm
  for an already-mapped document is a no-op that returns the existing record.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditLog
from apps.inventory.models import Product, ProductCategory, StockMovement
from apps.inventory.services import post_movement
from .models import DocumentMapping, Party, Transaction, TransactionLine


def _dec(v, default=None):
    if v in (None, ""):
        return default
    try:
        return Decimal(str(v)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return default


def detect_kind(raw_json: dict) -> str:
    """Classify a document as sale / purchase / estimate."""
    dt = str((raw_json or {}).get("doc_type", "")).lower()
    if dt in (Transaction.Kind.SALE, Transaction.Kind.PURCHASE,
              Transaction.Kind.ESTIMATE):
        return dt
    blob = " ".join(str(v) for v in (raw_json or {}).values()).lower()
    if "estimate" in blob or "quotation" in blob or "quote" in blob:
        return Transaction.Kind.ESTIMATE
    if "purchase" in blob or "vendor" in blob or "supplier" in blob:
        return Transaction.Kind.PURCHASE
    return Transaction.Kind.SALE


def ensure_mapping(document, store) -> DocumentMapping:
    """Create (or fetch) the PENDING mapping for a freshly extracted document."""
    mapping, created = DocumentMapping.objects.get_or_create(
        document=document,
        defaults={"store": store,
                  "detected_kind": detect_kind(document.raw_json)})
    return mapping


@transaction.atomic
def post_document(mapping: DocumentMapping, *, user, lines: list[dict],
                  kind: str = "", party_name: str = "",
                  number: str = "", date=None,
                  allow_negative: bool | None = None) -> Transaction:
    """Confirm a reviewed mapping into a Transaction + stock movements.

    ``lines`` items: {product_id?, new_product?{name,sku,category},
                      description, quantity, unit_price, amount}.
    """
    if mapping.status == DocumentMapping.Status.MAPPED and mapping.transaction:
        return mapping.transaction  # idempotent

    store = mapping.store
    kind = kind or mapping.detected_kind or detect_kind(mapping.document.raw_json)
    if allow_negative is None:
        allow_negative = store.allow_negative_stock

    party = None
    if party_name:
        party_kind = (Party.Kind.VENDOR if kind == Transaction.Kind.PURCHASE
                      else Party.Kind.CUSTOMER)
        party, _ = Party.objects.get_or_create(
            store=store, name=party_name.strip()[:160], kind=party_kind)

    doc = mapping.document
    txn = Transaction.objects.create(
        store=store, kind=kind, number=number or doc.invoice_number or "",
        party=party, date=date or doc.invoice_date,
        subtotal=doc.subtotal, tax=doc.tax, total=doc.total_amount,
        status=Transaction.Status.CONFIRMED, source_document=doc,
        created_by=user)

    for spec in lines:
        product = _resolve_product(store, spec, user)
        line = TransactionLine.objects.create(
            transaction=txn, product=product,
            description=str(spec.get("description", ""))[:255],
            quantity=_dec(spec.get("quantity"), Decimal("0")),
            unit_price=_dec(spec.get("unit_price")),
            amount=_dec(spec.get("amount")))
        # Stock effect: purchase = in (+), sale = out (-), estimate = none.
        if product and kind != Transaction.Kind.ESTIMATE and line.quantity:
            delta = line.quantity if kind == Transaction.Kind.PURCHASE \
                else -line.quantity
            reason = (StockMovement.Reason.PURCHASE
                      if kind == Transaction.Kind.PURCHASE
                      else StockMovement.Reason.SALE)
            post_movement(product, delta, reason, line=line, user=user,
                          allow_negative=allow_negative)

    mapping.transaction = txn
    mapping.detected_kind = kind
    mapping.status = DocumentMapping.Status.MAPPED
    mapping.mapped_by = user
    mapping.mapped_at = timezone.now()
    mapping.save(update_fields=["transaction", "detected_kind", "status",
                                "mapped_by", "mapped_at", "updated_at"])
    doc.is_saved = True
    doc.save(update_fields=["is_saved", "updated_at"])

    AuditLog.record_safe(user, AuditLog.Action.DATA_ACCESS,
                         target=f"doc:{doc.id}", op="map",
                         kind=kind, txn=txn.id)
    return txn


def _resolve_product(store, spec, user) -> Product | None:
    if spec.get("product_id"):
        return Product.objects.filter(store=store,
                                      pk=spec["product_id"]).first()
    np = spec.get("new_product")
    if np and np.get("name"):
        category = None
        if np.get("category"):
            category, _ = ProductCategory.objects.get_or_create(
                store=store, name=str(np["category"]).strip()[:80])
        sku = (np.get("sku") or _slug_sku(np["name"]))[:64]
        product, _ = Product.objects.get_or_create(
            store=store, sku=sku,
            defaults={"name": str(np["name"]).strip()[:200],
                      "category": category,
                      "cost_price": _dec(spec.get("unit_price")),
                      "sale_price": _dec(spec.get("unit_price"))})
        return product
    return None


def _slug_sku(name: str) -> str:
    import re
    base = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").upper()[:40]
    return base or "ITEM"
