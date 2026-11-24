"""`HANDLERS`: the table the loop uses to go from a stop reason to its handler."""

import handlers
from api.response import StopReason


def test_every_stop_reason_has_a_handler():
    """No stop reason we know about can reach the loop without code to deal with it."""
    assert set(handlers.HANDLERS) == set(StopReason)


def test_each_stop_reason_goes_to_its_own_handler():
    """The table is wired correctly: a refusal is never treated as, say, a final answer."""
    assert handlers.HANDLERS == {
        "tool_use": handlers.on_tool_use,
        "end_turn": handlers.on_end_turn,
        "max_tokens": handlers.on_max_tokens,
        "refusal": handlers.on_refusal,
        "model_context_window_exceeded": handlers.on_context_window_exceeded,
        "pause_turn": handlers.on_pause_turn,
        "stop_sequence": handlers.on_stop_sequence,
    }
