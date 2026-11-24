"""`on_tool_use`: run the tools the model asked for and queue their results.

The API is strict here: the assistant message holding the `tool_use` blocks must be
followed straight away by a user message with one `tool_result` per call, matched by id.
"""

import json

import db
from handlers.tool_use import on_tool_use
from state import AgentState
from utils import utils


def test_call_is_answered_by_a_matching_result(tool_call, message):
    """The model's request is stored first, then the answer carrying the same id."""
    state = AgentState.start("hi")

    stop = on_tool_use(state, message("tool_use", tool_call("t1", "get_card", id="2")))

    assert stop is False
    assert [m["role"] for m in state.session] == ["user", "assistant", "user"]
    assert state.session[1]["content"][0]["id"] == "t1"
    (result,) = state.session[2]["content"]
    assert result["type"] == "tool_result"
    assert result["tool_use_id"] == "t1"
    assert result["is_error"] is False
    assert json.loads(result["content"])["cards"][0]["title"] == "Team standup"


def test_parallel_calls_are_all_run_and_answered_together(text, tool_call, message):
    """Several calls in one response all run, in order, and share one user message.

    Text around the calls is kept in the conversation but is not treated as a call.
    """
    state = AgentState.start("hi")

    on_tool_use(
        state,
        message(
            "tool_use",
            text("On it."),
            tool_call("t1", "create_card", title="New", content="x"),
            tool_call("t2", "delete_card", id="1"),
        ),
    )

    assert [b["type"] for b in state.session[1]["content"]] == ["text", "tool_use", "tool_use"]
    assert [r["tool_use_id"] for r in state.session[2]["content"]] == ["t1", "t2"]
    assert [c.id for c in db.list_cards()] == ["2", "3", "4"]
    assert state.metadata["tool_calls"] == [
        {"create_card": {"title": "New", "content": "x"}},
        {"delete_card": {"id": "1"}},
    ]


def test_one_failing_call_does_not_stop_the_others(tool_call, message):
    """A bad call is reported to the model as an error; the good one still succeeds."""
    state = AgentState.start("hi")

    on_tool_use(
        state,
        message("tool_use", tool_call("t1", "nope"), tool_call("t2", "list_cards")),
    )

    assert [r["is_error"] for r in state.session[2]["content"]] == [True, False]


def test_cap_bumped_by_an_earlier_truncation_is_reset(tool_call, message):
    """Extra room granted to survive one truncation does not stick to later requests."""
    state = AgentState.start("hi")
    state.bump_max_tokens()

    on_tool_use(state, message("tool_use", tool_call("t1", "list_cards")))

    assert state.max_tokens == utils.set_max_tokens_cap()
    assert state.max_tokens_capped is False


def test_open_continue_run_is_closed_before_the_results(text, tool_call, message):
    """Pieces are merged into one message, and the results still come right after it."""
    state = AgentState.start("hi", cutover_index=1)
    state.session.append({"role": "assistant", "content": [{"type": "text", "text": "Let me "}]})
    state.append_user("continue")

    on_tool_use(state, message("tool_use", text("look."), tool_call("t1", "list_cards")))

    assert state.cutover_index is None
    assert [m["role"] for m in state.session] == ["user", "assistant", "user"]
    first, second, call = state.session[1]["content"]
    assert (first["text"], second["text"]) == ("Let me ", "look.")
    assert call["id"] == "t1"
    assert state.session[2]["content"][0]["tool_use_id"] == "t1"
