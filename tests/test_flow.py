"""Integration: upload row -> process (mock) -> stored doc + items."""
import io
import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db
User = get_user_model()


def _user():
    u = User.objects.create_user("alice", "alice@example.com", "Str0ng!Pass")
    u.is_active = True; u.is_approved = True; u.role = "analyst"; u.save()
    return u


def test_upload_to_extraction(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.GEMINI_API_KEY = ""  # force mock
    from apps.uploads.models import UploadSession, UploadedFile, Status
    from apps.processing.tasks import process_file
    from apps.processing.models import ExtractedDocument
    from django.core.files.base import ContentFile

    u = _user()
    session = UploadSession.objects.create(uploaded_by=u)
    text = b"Invoice No: INV-1\nVendor: Acme\nTotal: 20.00\nWidget   2   10.00\n"
    uf = UploadedFile.objects.create(
        session=session, uploaded_by=u, original_name="inv.txt",
        content_type="text/plain", size_bytes=len(text), status=Status.PENDING)
    uf.file.save("inv.txt", ContentFile(text))

    res = process_file(uf.id)
    assert res["ok"] is True
    doc = ExtractedDocument.objects.get(uploaded_file=uf)
    assert doc.invoice_number == "INV-1"
    assert doc.items.count() == 1


def test_save_to_db_with_new_category(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.GEMINI_API_KEY = ""
    from rest_framework.test import APIClient
    from apps.uploads.models import UploadSession, UploadedFile, Status
    from apps.processing.tasks import process_file
    from django.core.files.base import ContentFile

    u = _user()
    s = UploadSession.objects.create(uploaded_by=u)
    text = b"Invoice No: INV-2\nVendor: Beta\nTotal: 5.00\n"
    uf = UploadedFile.objects.create(session=s, uploaded_by=u,
        original_name="b.txt", content_type="text/plain",
        size_bytes=len(text), status=Status.PENDING)
    uf.file.save("b.txt", ContentFile(text))
    res = process_file(uf.id)

    client = APIClient(); client.force_authenticate(u)
    r = client.post(f"/api/processing/documents/{res['document_id']}/save_to_db/",
                    {"new_category": "Utilities"}, format="json")
    assert r.status_code == 200
    assert r.data["is_saved"] is True
    assert r.data["category"]["name"] == "Utilities"


def test_viewer_role_cannot_upload(tmp_path, settings):
    from rest_framework.test import APIClient
    u = User.objects.create_user("vic", "vic@example.com", "Str0ng!Pass")
    u.is_active = True; u.is_approved = True; u.role = "viewer"; u.save()
    client = APIClient(); client.force_authenticate(u)
    # categories create requires CanUpload
    r = client.post("/api/processing/categories/", {"name": "X"}, format="json")
    assert r.status_code in (403, 401)
