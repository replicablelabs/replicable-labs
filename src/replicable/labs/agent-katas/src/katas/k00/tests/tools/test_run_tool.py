"""The tool runner and the @tool decorator."""

import pytest

from katas.k00.tools import run_tool


def test_run_tool_reports_bad_calls_as_errors():
    assert run_tool("nope", {})[1] is True
    assert run_tool("get_card", {"bogus": 1})[1] is True
    assert run_tool("schedule_card", {"id": "1"})[1] is True   # missing scheduled_at


def test_tools_must_return_a_result_model():
    from katas.k00.tools.base import tool

    @tool
    def bad() -> str:
        """Returns a plain dict-like string instead of a model."""
        return "{}"

    with pytest.raises(AssertionError):
        bad.call({})
