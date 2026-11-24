"""The tool runner and the @tool decorator.

Whatever goes wrong inside a tool, the model must get a readable error back and the loop
must survive.
"""

from types import SimpleNamespace

import pytest

import tools
from tools import run_tool
from tools.schemas import Result, Status
from utils.utils import ToolError


def test_run_tool_reports_bad_calls_as_errors():
    """A call the model got wrong becomes an error it can read and fix, not a crash."""
    assert run_tool("nope", {})[1] is True
    assert run_tool("get_card", {"bogus": 1})[1] is True
    assert run_tool("schedule_card", {"id": "1"})[1] is True   # missing scheduled_at


def test_tools_must_return_a_result_model():
    """A tool that forgets the shared result shape is caught instead of reaching the model."""
    from tools.base import tool

    @tool
    def bad() -> str:
        """Returns a plain dict-like string instead of a model."""
        return "{}"

    with pytest.raises(AssertionError):
        bad.call({})


def test_unknown_tool_error_lists_the_real_ones():
    """The model can recover from a wrong name because the error shows the right ones."""
    content, _ = run_tool("nope", {})
    assert "'nope'" in content and all(name in content for name in tools.TOOLS)


@pytest.mark.parametrize(
    "error,content",
    [
        (ToolError("give an id"), "give an id"),
        (TypeError("bad type"), "Invalid arguments for broken: bad type"),
        (ValueError("bad value"), "Invalid arguments for broken: bad value"),
        (KeyError("k"), "broken failed: KeyError: 'k'"),
    ],
)
def test_every_kind_of_exception_becomes_an_error_result(monkeypatch, error, content):
    """A tool's own message, a bad argument and a plain bug each read differently."""

    def explode(tool_input):
        raise error

    monkeypatch.setitem(tools.TOOLS, "broken", SimpleNamespace(call=explode))
    assert run_tool("broken", {}) == (content, True)


def test_results_are_json_without_unset_fields():
    """The model reads compact JSON: fields that were never set are left out."""

    @tools.base.tool
    def good() -> Result:
        """Returns an empty list."""
        return Result(status=Status.LISTED)

    assert good.call({}) == '{"status":"listed","cards":[]}'
