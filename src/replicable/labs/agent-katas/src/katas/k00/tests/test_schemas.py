"""The contract between the tool code and the model: definitions match the code."""

import inspect

import pytest
from katas.k00.tools import SCHEMAS, TOOLS
from katas.k00.tools.schemas import Status

TOTAL_TOOLS_SO_FAR = 6


def test_tool_definitions_come_from_docstrings():
    """Test whether the values that the model receives for each tool's name,
    description, parameters and required list match the tool signature.
    """
    assert len(SCHEMAS) == len(TOOLS) == TOTAL_TOOLS_SO_FAR
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
        required = {
            p for p, v in params.items() if v.default is inspect.Parameter.empty
        }
        assert set(schema["input_schema"].get("required", [])) == required, name


# One real call per way a tool can return a status: (tool, arguments, status).
STATUS_CASES = [
    ("create_card", dict(title="New", content="x"), Status.CREATED),
    ("create_card", dict(title="Buy milk", content="x"), Status.EXISTS),
    ("create_card", dict(title="Buy milk", content="x", replace=True), Status.REPLACED),
    ("get_card", dict(id="1"), Status.FOUND),
    ("get_card", dict(id="99"), Status.NOT_FOUND),
    ("delete_card", dict(id="1"), Status.DELETED),
    ("delete_card", dict(id="99"), Status.NOT_FOUND),
    ("schedule_card", dict(id="1", scheduled_at="2026-11-25T09:00"), Status.SCHEDULED),
    ("schedule_card", dict(id="99", scheduled_at="2026-11-25T09:00"), Status.NOT_FOUND),
    ("find_card", dict(title="milk"), Status.LISTED),
    ("list_cards", dict(), Status.LISTED),
]


@pytest.mark.parametrize("tool,args,status", STATUS_CASES)
def test_every_status_a_tool_returns_is_documented(call, tool, args, status):
    """Test whether the status that the model receives out of a tool execution
    is named in the tool's description.
    """
    out, err = call(tool, **args)
    assert not err and out["status"] == status
    assert f'"{status.value}"' in TOOLS[tool].to_dict()["description"]


def test_every_status_is_exercised_by_a_case():
    """Test whether every member of katas.k00.tools.schemas.Status has a case in
    STATUS_CASES, such that new status can't go untested.
    """
    assert {status for _, _, status in STATUS_CASES} == set(Status)


def test_every_status_in_the_contract_is_documented_by_some_tool():
    """Test whether every member of katas.k00.tools.schemas.Status is described
    by at least one tool, such that statuses aren't defined without a purpose.
    """
    descriptions = " ".join(s["description"] for s in SCHEMAS)
    for status in Status:
        assert f'"{status.value}"' in descriptions, status


@pytest.mark.parametrize("name", TOOLS)
def test_every_argument_is_mentioned_in_brackets_in_the_description(name):
    """Test whether each tool description mentions each tool argument
    enclosed in '[', ']' to assist the model to identify tool arguments
    unambiguously.
    """
    tool = TOOLS[name]
    description = tool.to_dict()["description"]
    for param in inspect.signature(tool.func).parameters:
        assert f"[{param}]" in description, f"{name}: [{param}] not in the description"


@pytest.mark.parametrize("name", TOOLS)
def test_every_description_names_the_result_keys(name):
    """Test whether each tool description names the result keys the model reads,
    `[status]` and `[cards]`, and `[message]` where it can say `not_found`.
    """
    description = TOOLS[name].to_dict()["description"]
    for key in ("status", "cards"):
        assert f"[{key}]" in description, f"{name}: [{key}] not in the description"
    if f'"{Status.NOT_FOUND.value}"' in description:
        assert "[message]" in description, f"{name}: [message] not in the description"


@pytest.mark.parametrize("tool,args,status", STATUS_CASES)
def test_every_result_has_a_status_and_a_cards_list(call, tool, args, status):
    """Test whether every tool returns `status` and a `cards` list, empty or
    not, so the model reads one shape for all tools.
    """
    out, err = call(tool, **args)
    assert not err and isinstance(out["cards"], list)
    if status == Status.NOT_FOUND:
        assert out["cards"] == []
