"""Shared fixtures: a fresh card store, a tool caller, and stand-ins for model responses.

The response fixtures build real `anthropic` SDK objects, so tests exercise the same
types the API returns without calling it.
"""

import json
import os

import dotenv
import pytest
from anthropic.types import Message, TextBlock, ThinkingBlock, ToolUseBlock, Usage

# Tests never send traces, even if the shell exports LANGSMITH_TRACING.
os.environ["LANGSMITH_TRACING"] = "false"
# Importing `cli` loads the lab's .env; keep real credentials and settings out of the tests.
dotenv.load_dotenv = lambda *args, **kwargs: False

import db  # noqa: E402
from tools import run_tool  # noqa: E402
from utils.log import logger  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Reset the card store to its seed data before every test."""
    db.reset()


@pytest.fixture
def call():
    """Call a tool by name; returns (parsed result or error text, is_error)."""

    def _call(name, **kwargs):
        """Run the tool `name` with `kwargs` as its input."""
        content, is_error = run_tool(name, kwargs)
        return (content if is_error else json.loads(content)), is_error

    return _call


@pytest.fixture
def text():
    """Build a text block: `text("Hello")`."""
    return lambda value: TextBlock(type="text", text=value)


@pytest.fixture
def thinking():
    """Build a thinking block: `thinking("hmm")`."""
    return lambda value: ThinkingBlock(type="thinking", thinking=value, signature="s")


@pytest.fixture
def tool_call():
    """Build a `tool_use` block: `tool_call("t1", "get_card", id="2")`."""

    def _tool_call(call_id, tool_name, /, **tool_input):
        return ToolUseBlock(type="tool_use", id=call_id, name=tool_name, input=tool_input)

    return _tool_call


@pytest.fixture
def message():
    """Build a model response: `message("end_turn", text("Hello"))`."""

    def _message(stop_reason, *blocks):
        return Message(
            id="msg_test",
            type="message",
            role="assistant",
            model="test-model",
            content=list(blocks),
            stop_reason=stop_reason,
            usage=Usage(input_tokens=1, output_tokens=1),
        )

    return _message


@pytest.fixture
def logs(caplog):
    """Capture the lab's logger, which `caplog` misses because it does not propagate."""
    logger.addHandler(caplog.handler)
    yield caplog
    logger.removeHandler(caplog.handler)
