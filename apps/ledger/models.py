"""Unified sales/purchase ledger + OCR document mapping audit."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.stores.models import Store
from apps.inventory.models import Product


class Party(TimeStampedModel):
    class Kind(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        VENDOR = "vendor", "Vendor"

    store = models.ForeignKey(Store, on_delete=models.CASCADE,
                              related_name="parties")
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    phone = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name_plural = "parties"
        indexes = [models.Index(fields=["store", "kind", "name"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.kind})"


class Transaction(TimeStampedModel):
    class Kind(models.TextChoices):
        SALE = "sale", "Sale"
        PURCHASE = "purchase", "Purchase"
        ESTIMATE = "estimate", "Estimate"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        VOID = "void", "Void"

    store = models.ForeignKey(Store, on_delete=models.CASCADE,
                              related_name="transactions", db_index=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, db_index=True)
    number = models.CharField(max_length=60, blank=True)
    party = models.ForeignKey(Party, null=True, blank=True,
                              on_delete=models.SET_NULL,
                              related_name="transactions")
    date = models.DateField(null=True, blank=True, db_index=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2,
                                   null=True, blank=True)
    tax = models.DecimalField(max_digits=14, decimal_places=2,
                              null=True, blank=True)
    total = models.DecimalField(max_digits=14, decimal_places=2,
                                null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.DRAFT, db_index=True)
    source_document = models.ForeignKey(
        "processing.ExtractedDocument", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="transactions")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                   blank=True, on_delete=models.SET_NULL)

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["store", "kind", "date"])]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.number or self.pk}"


class TransactionLine(TimeStampedModel):
    """Canonical structured line (the operational source of truth for lines)."""
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE,
                                    related_name="lines")
    product = models.ForeignKey(Product, null=True, blank=True,
                                on_delete=models.SET_NULL,
                                related_name="transaction_lines")
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2,
                                     null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2,
                                 null=True, blank=True)

    def __str__(self) -> str:
        return self.description or (self.product.name if self.product else "line")


class DocumentMapping(TimeStampedModel):
    """Audit binding a Gemini-extracted document to the transaction it produced."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        MAPPED = "mapped", "Mapped"
        REJECTED = "rejected", "Rejected"

    document = models.OneToOneField("processing.ExtractedDocument",
                                    on_delete=models.CASCADE,
                                    related_name="mapping")
    store = models.ForeignKey(Store, on_delete=models.CASCADE,
                              related_name="document_mappings")
    transaction = models.ForeignKey(Transaction, null=True, blank=True,
                                    on_delete=models.SET_NULL,
                                    related_name="mappings")
    detected_kind = models.CharField(max_length=10,
                                     choices=Transaction.Kind.choices,
                                     blank=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    field_map = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    mapped_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                  blank=True, on_delete=models.SET_NULL)
    mapped_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Mapping doc:{self.document_id} [{self.status}]"
