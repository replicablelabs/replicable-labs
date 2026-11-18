import pytest
from katas.loader import load
from katas.world import World

issue_refund = load("k03_tool_errors").issue_refund

def ok(w, oid="1001", amount=10.0): return issue_refund(w, oid, amount, "damaged")

def test_success_records_refund_and_returns_id():
    w = World(); content, err = ok(w)
    assert err is False and "R-1001-1" in content and w.refunded("1001") == 10.0

def test_unknown_order_is_error_not_exception():
    content, err = ok(World(), "9999")
    assert err is True and "not found" in content.lower()

def test_not_delivered_error_names_the_status():
    content, err = ok(World(), "1002")
    assert err is True and "delivered" in content and "shipped" in content

def test_too_old_error_mentions_the_30_day_window():
    content, err = ok(World(), "1004", 5.0)
    assert err is True and "30 days" in content

def test_amount_above_balance_error_states_the_maximum():
    content, err = ok(World(), "1001", 500.0)
    assert err is True and "49.90" in content

def test_cumulative_refunds_cannot_exceed_total_and_error_shows_remaining():
    w = World(); assert ok(w, amount=40.0)[1] is False
    content, err = ok(w, amount=20.0)
    assert err is True and "9.90" in content and w.refunded("1001") == 40.0

@pytest.mark.parametrize("bad", [0, -5, "ten", None, True])
def test_invalid_amounts_rejected_without_side_effects(bad):
    w = World(); content, err = issue_refund(w, "1001", bad, "x")
    assert err is True and w.refunds == {}
