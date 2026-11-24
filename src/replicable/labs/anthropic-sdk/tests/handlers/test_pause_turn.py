"""`on_pause_turn`: a placeholder until the stop reason is handled.

This pins today's behaviour; replace it when the handler's TODO is done.
"""

from handlers.pause_turn import on_pause_turn
from state import AgentState


def test_warns_and_resends_the_same_request(message, logs):
    """The gap is visible in the log, and the conversation is left untouched."""
    state = AgentState.start("hi")

    assert on_pause_turn(state, message("pause_turn")) is False

    assert "pause_turn is not handled" in logs.text
    assert state == AgentState.start("hi")
