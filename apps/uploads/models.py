"""Upload session + per-file tracking with processing status."""
from __future__ import annotations

import hashlib
import os

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


def upload_path(instance, filename):
    return f"uploads/{instance.uploaded_by_id or 'anon'}/{instance.session_id}/{filename}"


class UploadSession(TimeStampedModel):
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.CASCADE,
                                    related_name="upload_sessions")
    note = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Session {self.pk} by {self.uploaded_by_id}"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class UploadedFile(TimeStampedModel):
    session = models.ForeignKey(UploadSession, on_delete=models.CASCADE,
                                related_name="files")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.CASCADE,
                                    related_name="files", db_index=True)
    file = models.FileField(upload_to=upload_path)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    error = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["uploaded_by", "status"])]

    def __str__(self):
        return f"{self.original_name} [{self.status}]"

    def compute_hash(self):
        h = hashlib.sha256()
        for chunk in self.file.chunks():
            h.update(chunk)
        self.sha256 = h.hexdigest()
        return self.sha256

    def mark(self, status, error="", commit=True):
        from django.utils import timezone
        self.status = status
        if error:
            self.error = error
        if status in (Status.COMPLETED, Status.FAILED):
            self.processed_at = timezone.now()
        if commit:
            self.save(update_fields=["status", "error", "processed_at", "updated_at"])
