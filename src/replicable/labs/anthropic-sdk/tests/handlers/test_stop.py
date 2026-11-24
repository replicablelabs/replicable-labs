"""The dead ends: a refusal, a full context window and an unknown stop reason.

Sending the same request again is not expected to help, so all must report and stop.
"""

from types import SimpleNamespace

from handlers.stop import on_context_window_exceeded, on_refusal, on_unknown
from state import AgentState


def test_refusal_stops_and_logs_why(logs):
    """The loop ends, the reason given by the API is logged, and nothing is stored."""
    state = AgentState.start("hi")

    assert on_refusal(state, SimpleNamespace(stop_details="policy-x")) is True

    assert "refused: policy-x" in logs.text
    assert len(state.session) == 1 and state.result == ""


def test_full_context_window_stops_and_is_logged(logs):
    """The history can only grow, so the loop ends instead of retrying forever."""
    state = AgentState.start("hi")

    assert on_context_window_exceeded(state, None) is True

    assert "context window exceeded" in logs.text
    assert len(state.session) == 1 and state.result == ""


def test_unknown_reason_stops_and_is_named(logs):
    """The log says which reason arrived, so it is clear what needs a handler."""
    state = AgentState.start("hi")

    assert on_unknown(state, SimpleNamespace(stop_reason="brand_new")) is True

    assert "unknown stop_reason: 'brand_new'" in logs.text
    assert len(state.session) == 1 and state.result == ""
