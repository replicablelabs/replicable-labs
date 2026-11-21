"""Tests for the k00_free sandbox: the db package and the card tools."""

import json

import pytest

from katas.k00_free import db
from katas.k00_free.tools import SCHEMAS, run_tool


@pytest.fixture(autouse=True)
def fresh_db():
    db.reset()


def call(name, **kwargs):
    content, is_error = run_tool(name, kwargs)
    return (content if is_error else json.loads(content)), is_error


# ---- db ----

def test_seed_and_ids():
    assert [c.id for c in db.list_cards()] == ["1", "2", "3"]
    assert db.add_card("New", "x").id == "4"


def test_reset_restarts_ids():
    db.add_card("New", "x")
    db.reset()
    assert [c.id for c in db.list_cards()] == ["1", "2", "3"]


@pytest.mark.parametrize(
    "id,title,expect_deleted",
    [
        (None, None, None),
        ("99", None, None),
        (None, "nope", None),
        ("1", "Team standup", None),   # id and title point at different cards
        ("1", "buy milk", "1"),
        (None, "Team standup", "2"),
        ("3", None, "3"),
    ],
)
def test_delete_card(id, title, expect_deleted):
    before = len(db.list_cards())
    deleted = db.delete_card(id, title)
    assert (deleted.id if deleted else None) == expect_deleted
    assert len(db.list_cards()) == before - (1 if expect_deleted else 0)


def test_fuzzy_search_ranks_and_scores():
    hits = db.fuzzy_search_cards("lisbon flights")
    assert hits[0].title == "Book flights" and hits[0].score is not None
    assert db.fuzzy_search_cards("") == []


# ---- tools ----

def test_tool_definitions_come_from_docstrings():
    import inspect
    from katas.k00_free.tools import TOOLS

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
def test_every_status_a_tool_returns_is_documented(tool, args, status):
    from katas.k00_free.tools import TOOLS

    out, err = call(tool, **args)
    assert not err and out["status"] == status
    assert f'"{status}"' in TOOLS[tool].to_dict()["description"]


def test_every_status_in_the_contract_is_documented_by_some_tool():
    from typing import get_args

    from katas.k00_free.tools.schemas import Status

    descriptions = " ".join(s["description"] for s in SCHEMAS)
    for status in get_args(Status):
        assert f'"{status}"' in descriptions, status


def test_tools_must_return_a_result_model():
    from katas.k00_free.tools.base import tool

    @tool
    def bad() -> str:
        """Returns a plain dict-like string instead of a model."""
        return "{}"

    with pytest.raises(AssertionError):
        bad.call({})


@pytest.mark.parametrize("tool,key", [("find_card", "matches"), ("list_cards", "cards")])
def test_list_results_name_their_key_in_the_description(tool, key):
    from katas.k00_free.tools import TOOLS

    out, err = call(tool, **({"title": "milk"} if tool == "find_card" else {}))
    assert not err and key in out
    assert f"[{key}]" in TOOLS[tool].to_dict()["description"]


def test_list_cards():
    out, err = call("list_cards")
    assert not err and [c["id"] for c in out["cards"]] == ["1", "2", "3"]


def test_get_card():
    assert call("get_card", id="2")[0]["card"]["title"] == "Team standup"
    assert call("get_card", title="BUY MILK")[0]["status"] == "found"
    assert call("get_card", id="99")[0]["status"] == "not_found"
    assert call("get_card", id="1", title="Team standup")[0]["status"] == "not_found"
    out, err = call("get_card")
    assert err


def test_find_card():
    out, err = call("find_card", content="lisbon")
    assert not err and out["matches"][0]["title"] == "Book flights"
    assert call("find_card", id="1")[0]["matches"][0]["id"] == "1"
    assert call("find_card", title="zzzzzz")[0]["matches"] == []
    assert call("find_card")[1] is True


def test_create_card_flow():
    out, _ = call("create_card", title="Capital of France", content="Paris")
    assert out["status"] == "created" and out["card"]["id"] == "4"

    out, _ = call("create_card", title="capital of france", content="Lyon")
    assert out["status"] == "exists" and out["card"]["content"] == "Paris"

    out, _ = call("create_card", title="Capital of France", content="Lyon", replace=True)
    assert out["status"] == "replaced" and out["card"]["id"] == "4"
    assert call("get_card", id="4")[0]["card"]["content"] == "Lyon"


def test_delete_card_tool():
    out, _ = call("delete_card", title="Buy milk")
    assert out["status"] == "deleted"
    assert call("delete_card", id="1")[0]["status"] == "not_found"
    assert call("delete_card")[1] is True


def test_schedule_card():
    out, _ = call("schedule_card", id="1", scheduled_at="2026-11-25T09:00")
    assert out["status"] == "scheduled" and out["card"]["scheduled_at"] == "2026-11-25T09:00:00"
    assert call("get_card", id="1")[0]["card"]["scheduled_at"] == "2026-11-25T09:00:00"
    assert call("schedule_card", id="99", scheduled_at="2026-11-25")[0]["status"] == "not_found"
    msg, err = call("schedule_card", id="1", scheduled_at="next tuesday")
    assert err and "ISO 8601" in msg


def test_run_tool_reports_bad_calls_as_errors():
    assert run_tool("nope", {})[1] is True
    assert run_tool("get_card", {"bogus": 1})[1] is True
    assert run_tool("schedule_card", {"id": "1"})[1] is True   # missing scheduled_at
