"""Stock posting helpers — keep balance and movement ledger in lockstep."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import F

from .models import Product, StockMovement


class NegativeStockError(ValueError):
    pass


@transaction.atomic
def post_movement(product: Product, delta, reason, *, line=None, user=None,
                  allow_negative=False) -> StockMovement:
    """Append a stock movement and update the cached balance atomically."""
    delta = Decimal(str(delta))
    locked = Product.objects.select_for_update().get(pk=product.pk)
    new_qty = locked.quantity_on_hand + delta
    if new_qty < 0 and not allow_negative:
        raise NegativeStockError(
            f"'{locked.name}' would go negative ({new_qty}).")
    mv = StockMovement.objects.create(
        store=locked.store, product=locked, delta=delta, reason=reason,
        transaction_line=line, created_by=user)
    Product.objects.filter(pk=locked.pk).update(
        quantity_on_hand=F("quantity_on_hand") + delta)
    return mv


def resolve_or_suggest(store, name: str, sku: str = ""):
    """Find a matching product for an OCR line within a store, else None."""
    qs = Product.objects.filter(store=store, is_active=True)
    if sku:
        hit = qs.filter(sku__iexact=sku).first()
        if hit:
            return hit
    if name:
        hit = qs.filter(name__iexact=name).first()
        if hit:
            return hit
        return qs.filter(name__icontains=name[:24]).first()
    return None
