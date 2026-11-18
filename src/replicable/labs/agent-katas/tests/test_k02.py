import json
from katas.loader import load
from katas.world import World

lookup_order = load("k02_tool_output").lookup_order

def test_concise_and_relevant_for_normal_order():
    out = json.loads(lookup_order(World(), "1001"))
    assert out["status"] == "delivered" and out["total"] == 49.90 and out["delivered_on"] == "2026-11-10" and out["id"] == "1001"

def test_never_leaks_internal_or_payment_data():
    for oid in ("1001", "1004", "1005"):
        out = lookup_order(World(), oid)
        assert "internal_notes" not in out and "card_number" not in out and "4111" not in out and "378282" not in out

def test_large_orders_are_truncated_but_say_how_to_get_more():
    out = lookup_order(World(), "1005")
    assert len(out) < 1500
    d = json.loads(out)
    assert d["item_count"] == 120 and len(d["items"]) <= 10 and "include_items" in json.dumps(d)

def test_full_items_on_request():
    d = json.loads(lookup_order(World(), "1005", include_items=True))
    assert len(d["items"]) == 120

def test_reports_refunds_already_issued():
    w = World(); w.refunds["1001"] = [{"amount": 10.0, "reason": "x"}]
    assert json.loads(lookup_order(w, "1001"))["refunded_so_far"] == 10.0

def test_not_found_is_an_actionable_error_not_null():
    out = lookup_order(World(), "9999")
    assert out != "null" and out.startswith("ERROR") and "not found" in out and "9999" in out
