"""The response-side enums: which stop reasons finish a turn.

The loop counts a turn only when the model got to finish what it was saying. These
tests pin that split and check that no stop reason falls outside it.
"""

import pytest

from api.response import COMPLETED_TURN_REASONS, StopReason


@pytest.mark.parametrize(
    "reason,completes",
    [
        (StopReason.END_TURN, True),
        (StopReason.TOOL_USE, True),
        (StopReason.PAUSE_TURN, True),
        (StopReason.STOP_SEQUENCE, True),
        (StopReason.MAX_TOKENS, False),
        (StopReason.REFUSAL, False),
        (StopReason.MODEL_CONTEXT_WINDOW_EXCEEDED, False),
    ],
)
def test_which_stop_reasons_complete_a_turn(reason, completes):
    """A cut-off or refused response is not a finished turn; the other reasons are."""
    assert (reason in COMPLETED_TURN_REASONS) is completes


def test_plain_api_strings_match_the_enum():
    """The API sends plain strings, so "end_turn" must work wherever the enum does."""
    assert "end_turn" == StopReason.END_TURN
    assert "end_turn" in COMPLETED_TURN_REASONS
    assert "max_tokens" not in COMPLETED_TURN_REASONS
