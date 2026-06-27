"""Schema validation/coercion is pure-Python and Django-free."""
from apps.processing.schema import validate


def test_coerces_numbers_and_dates():
    raw = {"invoice_number": "INV-9", "vendor_name": " Acme ",
           "date": "26/06/2026", "total_amount": "$1,250.50",
           "items": [{"name": "Widget", "quantity": "2", "unit_price": "10",
                      "amount": "20"}]}
    v = validate(raw)
    assert v.data["invoice_number"] == "INV-9"
    assert v.data["vendor_name"] == "Acme"
    assert v.data["date"] == "2026-06-26"
    assert v.data["total_amount"] == 1250.50
    assert v.items[0]["amount"] == 20.0


def test_derives_total_from_items():
    v = validate({"items": [{"name": "a", "amount": 5},
                            {"name": "b", "amount": 7}]})
    assert v.data["total_amount"] == 12.0


def test_handles_garbage_gracefully():
    v = validate({"total_amount": "n/a", "date": "not-a-date", "items": "bad"})
    assert v.data["total_amount"] is None
    assert v.items == []
