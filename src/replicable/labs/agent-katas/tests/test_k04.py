import pytest
from katas.fakes import FakeClient, tool_use
from katas.loader import load

M = load("k04_structured_output")
GOOD = {"category": "billing", "urgency": "high", "needs_human": False}

def turn(**inp): return ("tool_use", [tool_use("t1", M.TOOL_NAME, **inp)])

def test_uses_a_forced_tool_with_an_enum_schema():
    c = FakeClient(turn(**GOOD))
    assert M.classify_ticket(c, "I was charged twice") == GOOD
    req = c.calls[0]
    assert req["tool_choice"] == {"type": "tool", "name": M.TOOL_NAME}
    schema = req["tools"][0]["input_schema"]
    assert schema["properties"]["category"]["enum"] == ["billing", "shipping", "account", "other"]
    assert schema["properties"]["urgency"]["enum"] == ["low", "medium", "high"]
    assert schema["properties"]["needs_human"]["type"] == "boolean" and set(schema["required"]) == set(GOOD)

def test_invalid_value_is_fed_back_as_a_tool_error_and_retried_once():
    c = FakeClient(turn(category="refunds", urgency="high", needs_human=False), turn(**GOOD))
    assert M.classify_ticket(c, "x") == GOOD
    fb = c.calls[1]["messages"][-1]["content"][0]
    assert fb["is_error"] is True and "category" in fb["content"]

def test_gives_up_after_the_retry_with_a_clear_error():
    bad = turn(category="refunds", urgency="high", needs_human=False)
    c = FakeClient(bad, bad, bad)
    with pytest.raises(ValueError, match="category"): M.classify_ticket(c, "x")
    assert len(c.calls) == 2

def test_wrong_type_for_boolean_is_rejected():
    c = FakeClient(turn(category="billing", urgency="low", needs_human="no"), turn(**GOOD))
    assert M.classify_ticket(c, "x") == GOOD
