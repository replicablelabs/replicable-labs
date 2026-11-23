"""`on_max_tokens`: retry is the default, stitching only behind the `continue` strategy."""

from types import SimpleNamespace

import pytest

from katas.k00.handlers.max_tokens import on_max_tokens
from katas.k00.state import AgentState, MaxTokensStrategy
from katas.k00.utils import utils


def block(type_, **fields):
    return SimpleNamespace(
        type=type_, model_dump=lambda exclude_none=True: {"type": type_, **fields}
    )


def truncated(*blocks):
    return SimpleNamespace(stop_reason="max_tokens", content=list(blocks))


TEXT = block("text", text="Capital of ")
TOOL = block("tool_use", id="t1", name="list_cards", input={})
THINKING = block("thinking", thinking="...")


@pytest.fixture(autouse=True)
def no_env_strategy(monkeypatch):
    monkeypatch.delenv("K00_MAX_TOKENS_STRATEGY", raising=False)


def test_default_strategy_is_retry():
    assert AgentState.start("hi").max_tokens_strategy is MaxTokensStrategy.RETRY


def test_strategy_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("K00_MAX_TOKENS_STRATEGY", "continue")
    assert AgentState.start("hi").max_tokens_strategy is MaxTokensStrategy.CONTINUE


@pytest.mark.parametrize(
    "content", [[TEXT], [TOOL], [TEXT, TOOL], [THINKING], [THINKING, TEXT]]
)
def test_retry_strategy_bumps_and_adds_no_messages(content):
    state = AgentState.start("hi")
    before = state.max_tokens

    stop = on_max_tokens(state, truncated(*content))

    assert stop is False
    assert state.max_tokens == before * 2
    assert state.max_tokens_capped is True
    assert len(state.session) == 1
    assert state.cutover_index is None


def test_continue_strategy_keeps_text_only_truncation():
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
    state = AgentState.start("hi", max_tokens_strategy=MaxTokensStrategy.CONTINUE)
    before = state.max_tokens

    assert on_max_tokens(state, truncated(*content)) is False

    assert state.max_tokens == before * 2
    assert len(state.session) == 1


def test_stops_when_the_cap_is_already_at_the_ceiling():
    state = AgentState.start("hi", max_tokens=utils.MAX_TOKENS_CEILING)

    assert on_max_tokens(state, truncated(TEXT)) is True
    assert state.max_tokens == utils.MAX_TOKENS_CEILING


def test_cap_is_clamped_to_the_ceiling():
    state = AgentState.start("hi", max_tokens=utils.MAX_TOKENS_CEILING - 1)

    assert on_max_tokens(state, truncated(TEXT)) is False
    assert state.max_tokens == utils.MAX_TOKENS_CEILING
