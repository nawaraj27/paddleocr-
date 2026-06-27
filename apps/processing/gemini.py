"""Token-optimized Gemini Vision extraction service.

Design for token efficiency:
* The system instruction (role + rules + schema) is built ONCE and cached per
  process, never repeated per file.
* The per-image user prompt is a single short line — no restated instructions.
* We request ``response_mime_type=application/json`` + a compact response schema
  so the model returns strict JSON (no markdown, no prose) and we don't spend
  output tokens on formatting.
* PDFs/images are sent as inline bytes; large images should be downsized by the
  caller before reaching here.

Security:
* User-controlled text never enters the instruction. Image bytes are data, not
  instructions; we also strip any model attempt to wrap JSON in prose.
* The API key is read from settings (environment) only.

When the SDK or key is unavailable, ``MockGeminiClient`` returns a deterministic
JSON object parsed from any embedded text, so the pipeline is runnable offline.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from .schema import RESPONSE_SCHEMA

# Built once; ~50 tokens. Reused for every call in the process.
_SYSTEM_INSTRUCTION = (
    "Extract invoice/receipt fields as strict JSON matching the schema. "
    "Set doc_type to sale, purchase, or estimate based on the document. "
    "Use null for missing fields. Numbers only for amounts. "
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
    _client = None
    _is_mock = False

    def __init__(self):
        self.model_name = settings.GEMINI_MODEL

    # -- client management (lazy, cached) ------------------------------
    def _get_client(self):
        if GeminiService._client is not None:
            return GeminiService._client
        try:
            if not settings.GEMINI_API_KEY:
                raise RuntimeError("no api key")
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            GeminiService._client = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=_SYSTEM_INSTRUCTION,
            )
            GeminiService._is_mock = False
        except Exception:
            GeminiService._client = MockGeminiClient()
            GeminiService._is_mock = True
        return GeminiService._client

    def extract(self, image_bytes: bytes, mime_type: str,
                embedded_text: str = "") -> GeminiResult:
        client = self._get_client()
        if isinstance(client, MockGeminiClient):
            return client.extract(image_bytes, mime_type, embedded_text)
        return self._extract_real(client, image_bytes, mime_type)

    def _extract_real(self, client, image_bytes, mime_type) -> GeminiResult:
        import google.generativeai as genai  # noqa: F401
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
            "max_output_tokens": settings.GEMINI_MAX_OUTPUT_TOKENS,
            "temperature": 0.0,
        }
        # Single short user part + the image. No repeated instructions.
        parts = [
            {"mime_type": mime_type, "data": image_bytes},
            "Extract.",
        ]
        resp = client.generate_content(
            parts, generation_config=generation_config,
            request_options={"timeout": settings.GEMINI_TIMEOUT_S})
        text = _response_text(resp)
        data = _coerce_json(text)
        usage = getattr(resp, "usage_metadata", None)
        return GeminiResult(
            raw_text=text, data=data, model=self.model_name,
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
