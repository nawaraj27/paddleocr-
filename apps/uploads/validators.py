"""Server-side upload validation + lightweight malicious-content checks."""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError

# Magic byte signatures for the formats we accept.
_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",          # followed by 'WEBP'
    b"%PDF": "application/pdf",
}


def validate_upload(django_file):
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if django_file.size > max_bytes:
        raise ValidationError(f"File exceeds {settings.MAX_UPLOAD_MB} MB limit.")
    if django_file.size == 0:
        raise ValidationError("Empty file.")

    head = django_file.read(16)
    django_file.seek(0)
    sniffed = _sniff(head)
    if sniffed is None:
        raise ValidationError("Unrecognized or unsupported file signature.")
    if sniffed not in settings.ALLOWED_UPLOAD_TYPES:
        raise ValidationError(f"Type '{sniffed}' is not allowed.")
    # Reject HTML/script smuggled into images.
    lowered = head.lower()
    if lowered.startswith(b"<") or b"<script" in lowered:
        raise ValidationError("File content looks like markup/script.")
    return sniffed


def _sniff(head: bytes):
    for sig, mime in _SIGNATURES.items():
        if head.startswith(sig):
            if sig == b"RIFF" and head[8:12] != b"WEBP":
                continue
            return mime
    return None
