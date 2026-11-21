"""The contract between the tool code and the model: definitions match the code."""

import inspect
from typing import get_args

import pytest

from katas.k00.tools import SCHEMAS, TOOLS
from katas.k00.tools.schemas import Status


def test_tool_definitions_come_from_docstrings():
    assert len(SCHEMAS) == len(TOOLS) == 6
    for name, tool in TOOLS.items():
        schema = tool.to_dict()
        assert schema["name"] == name
        assert schema["description"].strip(), name
        params = inspect.signature(tool.func).parameters
        props = schema["input_schema"].get("properties", {})
        assert set(props) == set(params), name
        # Every parameter is documented in the docstring's Args section.
        for pname, prop in props.items():
            assert prop.get("description"), f"{name}.{pname} has no Args entry"
        # Parameters without a default are exactly the required ones.
        required = {p for p, v in params.items() if v.default is inspect.Parameter.empty}
        assert set(schema["input_schema"].get("required", [])) == required, name


@pytest.mark.parametrize(
    "tool,args,status",
    [
        ("create_card", dict(title="New", content="x"), "created"),
        ("create_card", dict(title="Buy milk", content="x"), "exists"),
        ("create_card", dict(title="Buy milk", content="x", replace=True), "replaced"),
        ("get_card", dict(id="1"), "found"),
        ("get_card", dict(id="99"), "not_found"),
        ("delete_card", dict(id="1"), "deleted"),
        ("delete_card", dict(id="99"), "not_found"),
        ("schedule_card", dict(id="1", scheduled_at="2026-11-25T09:00"), "scheduled"),
        ("schedule_card", dict(id="99", scheduled_at="2026-11-25T09:00"), "not_found"),
    ],
)
def test_every_status_a_tool_returns_is_documented(call, tool, args, status):
    out, err = call(tool, **args)
    assert not err and out["status"] == status
    assert f'"{status}"' in TOOLS[tool].to_dict()["description"]


def test_every_status_in_the_contract_is_documented_by_some_tool():
    descriptions = " ".join(s["description"] for s in SCHEMAS)
    for status in get_args(Status):
        assert f'"{status}"' in descriptions, status


@pytest.mark.parametrize("tool", ["find_card", "list_cards"])
def test_list_results_name_their_key_in_the_description(call, tool):
    out, err = call(tool, **({"title": "milk"} if tool == "find_card" else {}))
    assert not err and "cards" in out
    assert "[cards]" in TOOLS[tool].to_dict()["description"]
