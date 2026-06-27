from apps.processing.gemini import GeminiService, MockGeminiClient, _coerce_json


def test_coerce_json_strips_markdown():
    assert _coerce_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _coerce_json('prefix {"a": 2} suffix') == {"a": 2}
    assert _coerce_json("garbage") == {}


def test_mock_extracts_from_text():
    txt = ("Invoice No: INV-7\nVendor: Globex\nDate: 2026-06-01\n"
           "Total: 49.50\nWidget   2   10.00\n")
    r = MockGeminiClient().extract(txt.encode(), "text/plain", txt)
    assert r.data["invoice_number"] == "INV-7"
    assert r.backend == "mock"
    assert any(i["name"] == "Widget" for i in r.data["items"])
