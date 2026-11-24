"""`AgentState`: the memory of one run, shared by the loop and the handlers.

The conversation has to keep the shape the API accepts, and the token cap has to go up
when a response is cut off and come back down once a turn completes.
"""

import pytest

from state import AgentState, MaxTokensStrategy
from utils import utils


def test_start_holds_only_the_prompt():
    """A new run is one user message with clean counters and no answer yet."""
    state = AgentState.start("hi")
    assert state.session == [{"role": "user", "content": "hi"}]
    assert state.metadata == {"steps": 0, "turns": 0, "tool_calls": []}
    assert state.max_tokens == utils.set_max_tokens_cap()
    assert state.max_tokens_capped is False
    assert state.cutover_index is None
    assert state.result == ""


def test_runs_do_not_share_memory():
    """What happens in one run never leaks into another."""
    one, two = AgentState.start("one"), AgentState.start("two")
    one.metadata["tool_calls"].append("x")
    one.append_user("more")
    assert two.metadata["tool_calls"] == [] and len(two.session) == 1


@pytest.mark.parametrize("value", ["continue", " CONTINUE "])
def test_strategy_variable_is_forgiving_about_case_and_spaces(monkeypatch, value):
    """A sloppily typed setting is still understood."""
    monkeypatch.setenv("MAX_TOKENS_STRATEGY", value)
    assert AgentState.start("hi").max_tokens_strategy is MaxTokensStrategy.CONTINUE


def test_unknown_strategy_is_rejected(monkeypatch):
    """A typo fails loudly instead of silently running another strategy."""
    monkeypatch.setenv("MAX_TOKENS_STRATEGY", "retyr")
    with pytest.raises(ValueError):
        AgentState.start("hi")


def test_explicit_strategy_beats_the_environment(monkeypatch):
    """A caller such as an eval can choose per run, whatever the shell exports."""
    monkeypatch.setenv("MAX_TOKENS_STRATEGY", "continue")
    state = AgentState.start("hi", max_tokens_strategy=MaxTokensStrategy.RETRY)
    assert state.max_tokens_strategy is MaxTokensStrategy.RETRY


def test_append_assistant_stores_plain_dicts(text):
    """SDK objects are converted, so the session can be sent straight back to the API."""
    state = AgentState.start("hi")
    state.append_assistant([text("Hello")])
    assert state.session[1:] == [
        {"role": "assistant", "content": [{"type": "text", "text": "Hello"}]}
    ]


def test_append_assistant_closes_an_open_continue_run(text):
    """The last piece is merged with the earlier ones into one message, and the run ends."""
    state = AgentState.start("hi", cutover_index=1)
    state.session.append({"role": "assistant", "content": [{"type": "text", "text": "Pa"}]})
    state.append_user("continue")

    state.append_assistant([text("ris")])

    assert state.session[1:] == [
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "Pa"}, {"type": "text", "text": "ris"}],
        }
    ]
    assert state.cutover_index is None


def test_bump_then_reset_returns_to_the_starting_cap():
    """A bump gives the retry more room, and a reset takes it away again."""
    state = AgentState.start("hi")
    start = state.max_tokens

    assert state.bump_max_tokens() is True
    assert state.max_tokens == start * 2 and state.max_tokens_capped is True

    state.reset_max_tokens()
    assert state.max_tokens == start and state.max_tokens_capped is False


def test_bump_refuses_at_the_ceiling():
    """With no room left it says so and changes nothing, so the caller can give up."""
    state = AgentState.start("hi", max_tokens=utils.MAX_TOKENS_CEILING)
    assert state.bump_max_tokens() is False
    assert state.max_tokens == utils.MAX_TOKENS_CEILING
    assert state.max_tokens_capped is False


def test_reset_keeps_a_cap_that_was_never_bumped():
    """A cap chosen by the caller is not a bump, so a reset leaves it alone."""
    state = AgentState.start("hi", max_tokens=777)
    state.reset_max_tokens()
    assert state.max_tokens == 777
