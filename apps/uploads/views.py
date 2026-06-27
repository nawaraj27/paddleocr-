"""HTML upload center + multi-file ingest endpoint (async kickoff)."""
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from apps.core.models import AuditLog
from .models import UploadSession, UploadedFile, Status
from .validators import validate_upload


class UploadCenterView(LoginRequiredMixin, TemplateView):
    template_name = "uploads/index.html"


class UploadIngestView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Accept multiple files, validate, persist, queue async processing."""
    raise_exception = True

    def test_func(self):
        return self.request.user.can_upload()

    def post(self, request):
        files = request.FILES.getlist("files")
        if not files:
            return JsonResponse({"ok": False, "error": "no files"}, status=400)

        session = UploadSession.objects.create(
            uploaded_by=request.user, note=request.POST.get("note", ""))
        results = []
        for f in files:
            try:
                mime = validate_upload(f)
            except ValidationError as e:
                results.append({"name": f.name, "ok": False,
                                "error": "; ".join(e.messages)})
                continue
            uf = UploadedFile(session=session, uploaded_by=request.user,
                              file=f, original_name=f.name[:255],
                              content_type=mime, size_bytes=f.size,
                              status=Status.PENDING)
            uf.save()
            uf.compute_hash()
            uf.save(update_fields=["sha256"])
            AuditLog.record(request, AuditLog.Action.UPLOAD,
                            target=uf.original_name, file_id=uf.id)
            _queue_processing(uf.id)
            results.append({"name": uf.original_name, "ok": True,
                            "file_id": uf.id, "status": uf.status})
        return JsonResponse({"ok": True, "session_id": session.id,
                             "files": results})


def _queue_processing(file_id: int):
    """Dispatch the Celery task (eager in dev)."""
    from apps.processing.tasks import process_file
    try:
        process_file.delay(file_id)
    except Exception:
        # Broker down: run inline so dev still works.
        process_file(file_id)
