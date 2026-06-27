"""Store-scoped inventory. Stock balance is a cached projection of an
append-only StockMovement ledger (single source of truth)."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.stores.models import Store


class ProductCategory(TimeStampedModel):
    store = models.ForeignKey(Store, on_delete=models.CASCADE,
                              related_name="product_categories")
    name = models.CharField(max_length=80)

    class Meta(TimeStampedModel.Meta):
        verbose_name_plural = "product categories"
        constraints = [models.UniqueConstraint(
            fields=["store", "name"], name="uniq_store_prodcat")]

    def __str__(self) -> str:
        return self.name


class Product(TimeStampedModel):
    store = models.ForeignKey(Store, on_delete=models.CASCADE,
                              related_name="products", db_index=True)
    category = models.ForeignKey(ProductCategory, null=True, blank=True,
                                 on_delete=models.SET_NULL,
                                 related_name="products")
    sku = models.CharField(max_length=64)
    name = models.CharField(max_length=200, db_index=True)
    unit = models.CharField(max_length=20, default="pcs")
    cost_price = models.DecimalField(max_digits=14, decimal_places=2,
                                     null=True, blank=True)
    sale_price = models.DecimalField(max_digits=14, decimal_places=2,
                                     null=True, blank=True)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2,
                                        default=0)
    quantity_on_hand = models.DecimalField(max_digits=14, decimal_places=2,
                                           default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta(TimeStampedModel.Meta):
        constraints = [models.UniqueConstraint(
            fields=["store", "sku"], name="uniq_store_sku")]
        indexes = [models.Index(fields=["store", "name"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"

    @property
    def low_stock(self) -> bool:
        return self.quantity_on_hand <= self.reorder_level


class StockMovement(TimeStampedModel):
    """Immutable, append-only. delta>0 stock in, delta<0 stock out."""

    class Reason(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        SALE = "sale", "Sale"
        ADJUSTMENT = "adjustment", "Adjustment"
        RETURN = "return", "Return"

    store = models.ForeignKey(Store, on_delete=models.CASCADE,
                              related_name="stock_movements")
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name="movements", db_index=True)
    delta = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.CharField(max_length=16, choices=Reason.choices)
    transaction_line = models.ForeignKey(
        "ledger.TransactionLine", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="movements")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                   blank=True, on_delete=models.SET_NULL)

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["store", "product", "created_at"])]

    def __str__(self) -> str:
        return f"{self.product} {self.delta:+} ({self.reason})"
