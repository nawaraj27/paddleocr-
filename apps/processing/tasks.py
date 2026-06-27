"""Celery pipeline: validate file -> Gemini extract -> validate JSON -> store."""
from __future__ import annotations

import time

from celery import shared_task

from apps.uploads.models import UploadedFile, Status
from .gemini import GeminiService
from .schema import validate, SchemaError
from .services import persist_extraction
from .models import ProcessingLog


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def process_file(self, file_id: int):
    try:
        uf = UploadedFile.objects.select_related("uploaded_by").get(pk=file_id)
    except UploadedFile.DoesNotExist:
        return {"ok": False, "error": "file not found"}

    uf.mark(Status.PROCESSING)
    t0 = time.perf_counter()
    try:
        with uf.file.open("rb") as fh:
            image_bytes = fh.read()
        embedded = ""
        if uf.content_type == "text/plain":
            embedded = image_bytes.decode("utf-8", "ignore")

        result = GeminiService().extract(image_bytes, uf.content_type, embedded)
        validated = validate(result.data)
        # auto-store as not-yet-"saved" so the user can review then confirm.
        doc = persist_extraction(uf, validated, model_version=result.model,
                                 is_saved=False)
        uf.mark(Status.COMPLETED)
        _log(uf, "extract", "completed", t0,
             f"{result.backend}: {len(validated.items)} items")
        return {"ok": True, "document_id": doc.id, "backend": result.backend}

    except SchemaError as e:
        uf.mark(Status.FAILED, error=f"schema: {e}")
        _log(uf, "validate", "failed", t0, str(e))
        return {"ok": False, "stage": "validation", "error": str(e)}
    except Exception as e:  # API/IO failure -> retry then fail gracefully
        _log(uf, "extract", "error", t0, str(e))
        try:
            raise self.retry(exc=e)
        except Exception:
            uf.mark(Status.FAILED, error=str(e))
            return {"ok": False, "stage": "gemini", "error": str(e)}


def _log(uf, stage, status, t0, message=""):
    ProcessingLog.objects.create(
        uploaded_file=uf, stage=stage, status=status, message=message[:1000],
        duration_ms=round((time.perf_counter() - t0) * 1000, 2))
