"""Extracted documents (JSON + normalized relational mapping for analytics)."""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel, Category
from apps.uploads.models import UploadedFile, Status


class ExtractedDocument(TimeStampedModel):
    uploaded_file = models.OneToOneField(
        UploadedFile, on_delete=models.CASCADE, related_name="extracted")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.CASCADE,
                                    related_name="documents", db_index=True)
    category = models.ForeignKey(Category, null=True, blank=True,
                                 on_delete=models.SET_NULL,
                                 related_name="documents")
    status = models.CharField(max_length=16, choices=Status.choices,
                              default=Status.COMPLETED, db_index=True)

    # raw JSON + denormalized fields for fast analytics
    raw_json = models.JSONField(default=dict)
    invoice_number = models.CharField(max_length=120, blank=True, db_index=True)
    vendor_name = models.CharField(max_length=200, blank=True, db_index=True)
    invoice_date = models.DateField(null=True, blank=True, db_index=True)
    currency = models.CharField(max_length=8, blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2,
                                   null=True, blank=True)
    tax = models.DecimalField(max_digits=14, decimal_places=2,
                              null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2,
                                       null=True, blank=True, db_index=True)

    # metadata
    model_version = models.CharField(max_length=60, blank=True)
    confidence = models.FloatField(default=0.0)
    is_saved = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        indexes = [
            models.Index(fields=["uploaded_by", "invoice_date"]),
            models.Index(fields=["vendor_name", "invoice_date"]),
        ]

    def __str__(self):
        return f"{self.invoice_number or 'doc'} / {self.vendor_name or '?'}"


class InvoiceItem(TimeStampedModel):
    document = models.ForeignKey(ExtractedDocument, on_delete=models.CASCADE,
                                 related_name="items")
    name = models.CharField(max_length=255, db_index=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2,
                                     null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2,
                                 null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.name


class ProcessingLog(TimeStampedModel):
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE,
                                      related_name="logs")
    stage = models.CharField(max_length=40)
    status = models.CharField(max_length=16)
    message = models.TextField(blank=True)
    duration_ms = models.FloatField(default=0.0)
