"""The agent loop, driven by a scripted model instead of the real API.

Each test hands the loop a list of canned responses and looks at two things: what the
loop sent for each request, and what it returned at the end.
"""

import copy
from types import SimpleNamespace

import agent
import pytest
from tools import SCHEMAS
from utils import utils


class ScriptedClient:
    """Stands in for `Anthropic`: replays `responses` and records every request."""

    def __init__(self, *responses):
        self.requests = []
        self._responses = iter(responses)
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **request):
        # The loop mutates one session list; copy it to keep what was sent at the time.
        self.requests.append(copy.deepcopy(request))
        return next(self._responses)


@pytest.fixture(autouse=True)
def no_tracing_or_env(monkeypatch):
    """Use the scripted client unwrapped and ignore the shell's strategy setting."""
    monkeypatch.setattr(agent.tracing, "wrap_client", lambda client: client)
    monkeypatch.delenv("MAX_TOKENS_STRATEGY", raising=False)


@pytest.fixture
def run_metadata(monkeypatch):
    """Collect what the loop reports to the trace."""
    seen = {}
    monkeypatch.setattr(agent, "set_run_metadata", lambda **kw: seen.update(kw))
    return seen


def test_simple_answer_takes_one_request(text, message, capsys):
    """The model answers straight away: one request, and its text is returned and printed."""
    client = ScriptedClient(message("end_turn", text("Hello")))

    assert agent.main(client, "hi") == "Hello"

    assert client.requests == [
        {
            "model": agent.MODEL,
            "max_tokens": utils.set_max_tokens_cap(),
            "messages": [{"role": "user", "content": "hi"}],
            "system": utils.get_system_prompt(),
            "tools": SCHEMAS,
        }
    ]
    assert capsys.readouterr().out.startswith("Hello\n")


def test_tool_result_is_sent_back_before_the_answer(
    text, tool_call, message, run_metadata
):
    """The model asks for a tool, sees its result on the next request, then answers."""
    client = ScriptedClient(
        message("tool_use", tool_call("t1", "list_cards")),
        message("end_turn", text("Three cards")),
    )

    assert agent.main(client, "how many?") == "Three cards"

    sent = client.requests[1]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[2]["content"][0]["tool_use_id"] == "t1"
    assert run_metadata == {
        "model": agent.MODEL,
        "steps": 2,
        "turns": 2,
        "stop_reason": "end_turn",
        "tool_calls": 1,
    }


def test_truncated_response_is_retried_with_more_room(text, message, run_metadata):
    """A cut-off response is thrown away and the same question is asked with a bigger cap.

    The retry costs a step, but only the response that finished counts as a turn.
    """
    client = ScriptedClient(
        message("max_tokens", text("Hel")), message("end_turn", text("Hello"))
    )

    assert agent.main(client, "hi") == "Hello"

    first, second = client.requests
    assert second["max_tokens"] == first["max_tokens"] * 2
    assert second["messages"] == first["messages"]
    assert (run_metadata["steps"], run_metadata["turns"]) == (2, 1)


def test_continue_strategy_stitches_the_answer(monkeypatch, text, message):
    """With the other strategy the model is told to continue and the pieces are joined."""
    monkeypatch.setenv("MAX_TOKENS_STRATEGY", "continue")
    client = ScriptedClient(
        message("max_tokens", text("Hel")),
        message("max_tokens", text("lo ")),
        message("end_turn", text("you")),
    )

    assert agent.main(client, "hi") == "Hello you"

    assert len(client.requests[2]["messages"]) == 5


def test_refusal_ends_the_run_without_an_answer(message, run_metadata, logs):
    """The loop stops at once and does not count the refusal as a turn."""
    client = ScriptedClient(message("refusal"))

    assert agent.main(client, "hi") == ""

    assert len(client.requests) == 1
    assert (run_metadata["stop_reason"], run_metadata["turns"]) == ("refusal", 0)


def test_loop_gives_up_after_max_steps(monkeypatch, tool_call, message, run_metadata):
    """A model that never stops calling tools cannot keep the agent running forever."""
    monkeypatch.setattr(agent, "MAX_STEPS", 3)
    responses = [
        message("tool_use", tool_call(f"t{i}", "list_cards")) for i in range(4)
    ]
    client = ScriptedClient(*responses)

    assert agent.main(client, "loop") == ""

    assert len(client.requests) == run_metadata["steps"] == 3


@pytest.mark.parametrize("reason", ["breaking_reason", None])
def test_unknown_stop_reason_is_reported_and_stops(reason, run_metadata, logs):
    """A stop reason added to the API later, or a missing one, is named in the log and in
    the trace; the run ends without an answer instead of guessing or retrying.
    """
    resp = SimpleNamespace(
        stop_reason=reason, content=[], usage=SimpleNamespace(output_tokens=0)
    )
    client = ScriptedClient(resp)

    assert agent.main(client, "hi") == ""

    assert len(client.requests) == 1
    assert f"unknown stop_reason: {reason!r}" in logs.text
    assert (run_metadata["stop_reason"], run_metadata["turns"]) == (reason, 0)


def test_trace_inputs_hold_the_prompt_only():
    """The client holds credentials and a connection, so it never goes into a trace."""
    assert agent._prompt_only({"client": object(), "prompt": "hi"}) == {"prompt": "hi"}
