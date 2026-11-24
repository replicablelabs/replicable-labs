"""`on_max_tokens`: what to do when the model is cut off mid-answer.

There are two ways out. `retry` (the default) throws the half answer away and asks again
with more room. `continue` keeps the text and asks the model to carry on. A half-written
tool call can never be continued, so it is always retried.
"""

from types import SimpleNamespace

import pytest

from handlers.max_tokens import on_max_tokens
from state import AgentState, MaxTokensStrategy
from utils import utils


def block(type_, **fields):
    """A minimal content block: a type, plus the dict it dumps to."""
    return SimpleNamespace(
        type=type_, model_dump=lambda exclude_none=True: {"type": type_, **fields}
    )


def truncated(*blocks):
    """A response that was cut off after `blocks`."""
    return SimpleNamespace(stop_reason="max_tokens", content=list(blocks))


TEXT = block("text", text="Capital of ")
TOOL = block("tool_use", id="t1", name="list_cards", input={})
THINKING = block("thinking", thinking="...")


@pytest.fixture(autouse=True)
def no_env_strategy(monkeypatch):
    """Start from the default strategy, whatever the shell exports."""
    monkeypatch.delenv("MAX_TOKENS_STRATEGY", raising=False)


def test_default_strategy_is_retry():
    """With nothing configured, the safe strategy is used."""
    assert AgentState.start("hi").max_tokens_strategy is MaxTokensStrategy.RETRY


def test_strategy_comes_from_the_environment(monkeypatch):
    """`MAX_TOKENS_STRATEGY` switches strategy without touching the code."""
    monkeypatch.setenv("MAX_TOKENS_STRATEGY", "continue")
    assert AgentState.start("hi").max_tokens_strategy is MaxTokensStrategy.CONTINUE


@pytest.mark.parametrize(
    "content", [[TEXT], [TOOL], [TEXT, TOOL], [THINKING], [THINKING, TEXT]]
)
def test_retry_strategy_bumps_and_adds_no_messages(content):
    """Whatever was cut off is dropped: same conversation, twice the room."""
    state = AgentState.start("hi")
    before = state.max_tokens

    stop = on_max_tokens(state, truncated(*content))

    assert stop is False
    assert state.max_tokens == before * 2
    assert state.max_tokens_capped is True
    assert len(state.session) == 1
    assert state.cutover_index is None


def test_continue_strategy_keeps_text_only_truncation():
    """Half an answer is kept (without thinking) and the model is asked to carry on.

    The position where the run started is remembered so the pieces can be merged later.
    """
    state = AgentState.start("hi", max_tokens_strategy=MaxTokensStrategy.CONTINUE)
    before = state.max_tokens

    stop = on_max_tokens(state, truncated(THINKING, TEXT))

    assert stop is False
    assert state.max_tokens == before
    assert state.cutover_index == 1
    assert [m["role"] for m in state.session] == ["user", "assistant", "user"]
    assert state.session[1]["content"] == [{"type": "text", "text": "Capital of "}]


@pytest.mark.parametrize("content", [[TOOL], [TEXT, TOOL], [THINKING]])
def test_continue_strategy_still_retries_tools_and_empty(content):
    """A cut-off tool call is unsafe and bare thinking is nothing to keep, so both retry."""
    state = AgentState.start("hi", max_tokens_strategy=MaxTokensStrategy.CONTINUE)
    before = state.max_tokens

    assert on_max_tokens(state, truncated(*content)) is False

    assert state.max_tokens == before * 2
    assert len(state.session) == 1


def test_stops_when_the_cap_is_already_at_the_ceiling():
    """With no more room to give, asking again is pointless, so the loop stops."""
    state = AgentState.start("hi", max_tokens=utils.MAX_TOKENS_CEILING)

    assert on_max_tokens(state, truncated(TEXT)) is True
    assert state.max_tokens == utils.MAX_TOKENS_CEILING


def test_cap_is_clamped_to_the_ceiling():
    """Doubling never asks for more than the model can output."""
    state = AgentState.start("hi", max_tokens=utils.MAX_TOKENS_CEILING - 1)

    assert on_max_tokens(state, truncated(TEXT)) is False
    assert state.max_tokens == utils.MAX_TOKENS_CEILING


def test_second_truncation_joins_the_same_run():
    """Cut off twice in a row, it is still one answer: the start of the run does not move."""
    state = AgentState.start("hi", max_tokens_strategy=MaxTokensStrategy.CONTINUE)

    on_max_tokens(state, truncated(TEXT))
    on_max_tokens(state, truncated(TEXT))

    assert state.cutover_index == 1
    assert [m["role"] for m in state.session] == [
        "user", "assistant", "user", "assistant", "user",
    ]
