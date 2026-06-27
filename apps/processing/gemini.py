"""Token-optimized Gemini Vision extraction service.

API key is fetched from the database via SettingsService (with 5-min cache).
Falls back to env var for backwards compatibility.
Key is never logged or exposed outside this module.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from apps.core.services.settings_service import (
    get_gemini_api_key, get_gemini_model,
    GeminiKeyMissingError,
)
from .schema import RESPONSE_SCHEMA

logger = logging.getLogger(__name__)

# Built once; ~50 tokens. Reused for every call in the process.
_SYSTEM_INSTRUCTION = (
    "Extract invoice/receipt fields as strict JSON matching the schema. "
    "Set doc_type to sale, purchase, or estimate based on the document. "
    "The invoice may be in Nepali (Devanagari script) or English — extract text "
    "exactly as written, preserving Nepali Unicode characters. "
    "Use null for truly missing fields, never substitute null for readable text. "
    "Numbers only for amounts. "
    "Return JSON only — no markdown, no commentary."
)


@dataclass
class GeminiResult:
    raw_text: str
    data: dict[str, Any]
    model: str
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    backend: str = "gemini"


class GeminiService:
    # Class-level cache: keyed by api_key so stale keys auto-invalidate
    _client = None
    _client_key: str = ""
    _client_model: str = ""

    def __init__(self):
        pass  # model/key resolved fresh from settings service each time

    def _get_client(self):
        try:
            api_key = get_gemini_api_key()
            model_name = get_gemini_model()
        except GeminiKeyMissingError:
            logger.warning("Gemini API key not configured — using mock extractor.")
            return MockGeminiClient()

        # Reset if key or model changed since last init
        if (GeminiService._client is None
                or GeminiService._client_key != api_key
                or GeminiService._client_model != model_name
                or isinstance(GeminiService._client, MockGeminiClient)):
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                GeminiService._client = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=_SYSTEM_INSTRUCTION,
                )
                GeminiService._client_key = api_key
                GeminiService._client_model = model_name
            except Exception:
                logger.warning("Gemini client init failed — using mock extractor.")
                GeminiService._client = MockGeminiClient()
                GeminiService._client_key = ""
                GeminiService._client_model = ""

        return GeminiService._client

    def extract(self, image_bytes: bytes, mime_type: str,
                embedded_text: str = "") -> GeminiResult:
        client = self._get_client()
        if isinstance(client, MockGeminiClient):
            return client.extract(image_bytes, mime_type, embedded_text)
        return self._extract_real(client, image_bytes, mime_type)

    def _extract_real(self, client, image_bytes, mime_type) -> GeminiResult:
        model_name = get_gemini_model()
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
            "max_output_tokens": getattr(settings, "GEMINI_MAX_OUTPUT_TOKENS", 1024),
            "temperature": 0.0,
        }
        parts = [
            {"mime_type": mime_type, "data": image_bytes},
            "Extract.",
        ]
        resp = client.generate_content(
            parts, generation_config=generation_config,
            request_options={"timeout": getattr(settings, "GEMINI_TIMEOUT_S", 60)})
        text = _response_text(resp)
        data = _coerce_json(text)
        usage = getattr(resp, "usage_metadata", None)
        return GeminiResult(
            raw_text=text, data=data, model=model_name,
            prompt_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
            backend="gemini")


def _response_text(resp) -> str:
    try:
        return resp.text
    except Exception:
        try:
            return resp.candidates[0].content.parts[0].text
        except Exception:
            return ""


def _coerce_json(text: str) -> dict:
    """Extract the first JSON object even if wrapped in stray prose/markdown."""
    if not text:
        return {}
    text = text.strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    start = text.find("{")
    if start == -1:
        return {}
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


class MockGeminiClient:
    """Offline deterministic extractor. Parses 'Key: value' lines from text."""

    def extract(self, image_bytes, mime_type, embedded_text="") -> GeminiResult:
        text = embedded_text
        if not text:
            try:
                text = (image_bytes or b"").decode("utf-8", "ignore")
            except Exception:
                text = ""
        data = self._parse(text)
        return GeminiResult(raw_text=json.dumps(data), data=data,
                            model="mock", prompt_tokens=len(text) // 4,
                            output_tokens=len(json.dumps(data)) // 4,
                            backend="mock")

    def _parse(self, text: str) -> dict:
        kv = {}
        for line in text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                kv[k.strip().lower()] = v.strip()

        def find(*keys):
            for k in keys:
                for kk, vv in kv.items():
                    if k in kk:
                        return vv
            return None

        items = []
        for line in text.splitlines():
            m = re.match(r"\s*(.+?)\s{2,}(\d+)\s+([\d.]+)", line)
            if m:
                qty = float(m.group(2))
                price = float(m.group(3))
                items.append({"name": m.group(1).strip(), "quantity": qty,
                              "unit_price": price, "amount": qty * price})
        return {
            "invoice_number": find("invoice no", "invoice number", "invoice"),
            "vendor_name": find("vendor", "bill to", "from", "merchant"),
            "date": find("date"),
            "currency": find("currency"),
            "subtotal": find("subtotal"),
            "tax": find("tax"),
            "total_amount": find("total"),
            "items": items,
            "_confidence": 0.6,
        }
