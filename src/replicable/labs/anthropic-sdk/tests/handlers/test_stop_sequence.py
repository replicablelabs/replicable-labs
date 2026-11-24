"""`on_stop_sequence`: a placeholder until the stop reason is handled.

This pins today's behaviour; replace it when the handler's TODO is done.
"""

from handlers.stop_sequence import on_stop_sequence
from state import AgentState


def test_warns_and_resends_the_same_request(message, logs):
    """The gap is visible in the log, and the conversation is left untouched."""
    state = AgentState.start("hi")

    assert on_stop_sequence(state, message("stop_sequence")) is False

    assert "stop_sequence is not handled" in logs.text
    assert state == AgentState.start("hi")
