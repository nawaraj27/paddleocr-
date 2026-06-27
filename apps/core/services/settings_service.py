"""Settings service — retrieves app-level config from DB with in-memory cache.

Security rules:
- The Gemini API key is NEVER logged or returned to callers outside this module.
- Cache TTL: 5 minutes. Refreshed automatically or on explicit invalidation.
- Falls back to environment variable if DB key is blank (backwards compat).
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# In-memory cache: {key: (value, expires_at)}
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 minutes


class GeminiKeyMissingError(RuntimeError):
    """Raised when no Gemini API key is configured anywhere."""


def _cache_get(key: str) -> Optional[str]:
    entry = _cache.get(key)
    if entry and time.monotonic() < entry[1]:
        return entry[0]
    return None


def _cache_set(key: str, value: str) -> None:
    _cache[key] = (value, time.monotonic() + _CACHE_TTL)


def _cache_invalidate(key: str) -> None:
    _cache.pop(key, None)


def get_gemini_api_key() -> str:
    """Return the Gemini API key. DB takes priority over env var.

    Raises GeminiKeyMissingError if no key is found anywhere.
    Never logs the key value.
    """
    cached = _cache_get("gemini_api_key")
    if cached:
        return cached

    key = _fetch_from_db() or _fetch_from_env()
    if not key:
        logger.warning("Gemini API key not configured.")
        raise GeminiKeyMissingError("Gemini API key not configured.")

    _cache_set("gemini_api_key", key)
    return key


def get_gemini_model() -> str:
    """Return Gemini model name. DB takes priority over env/default."""
    cached = _cache_get("gemini_model")
    if cached:
        return cached

    model = _fetch_model_from_db() or getattr(settings, "GEMINI_MODEL", "gemini-flash-lite-latest")
    _cache_set("gemini_model", model)
    return model


def is_gemini_configured() -> bool:
    """Safe check — returns True/False without raising or exposing key."""
    try:
        get_gemini_api_key()
        return True
    except GeminiKeyMissingError:
        return False


def invalidate_gemini_cache() -> None:
    """Force-refresh on next request. Call after updating key in DB."""
    _cache_invalidate("gemini_api_key")
    _cache_invalidate("gemini_model")


# --- private DB/env fetchers (no logging of values) ---

def _fetch_from_db() -> str:
    try:
        from apps.cms.models import SiteSettings
        obj = SiteSettings.objects.only("gemini_api_key").first()
        return (obj.gemini_api_key or "").strip() if obj else ""
    except Exception:
        return ""


def _fetch_model_from_db() -> str:
    try:
        from apps.cms.models import SiteSettings
        obj = SiteSettings.objects.only("gemini_model").first()
        return (obj.gemini_model or "").strip() if obj else ""
    except Exception:
        return ""


def _fetch_from_env() -> str:
    return (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
