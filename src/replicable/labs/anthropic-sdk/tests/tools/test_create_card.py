"""create_card: created / exists / replaced.

Titles are unique, and existing content is only overwritten when asked for explicitly.
"""

import pytest

import db
from tools.schemas import Status


def test_create_card_flow(call):
    """A new title makes a card; a taken one changes nothing until `replace` is set, and a
    replaced card keeps its id.
    """
    out, _ = call("create_card", title="Capital of France", content="Paris")
    assert out["status"] == Status.CREATED and out["cards"][0]["id"] == "4"

    out, _ = call("create_card", title="capital of france", content="Lyon")
    assert out["status"] == Status.EXISTS and out["cards"][0]["content"] == "Paris"

    out, _ = call("create_card", title="Capital of France", content="Lyon", replace=True)
    assert out["status"] == Status.REPLACED and out["cards"][0]["id"] == "4"
    assert call("get_card", id="4")[0]["cards"][0]["content"] == "Lyon"


def test_replace_on_a_new_title_just_creates(call):
    """`replace` with nothing to replace is an ordinary create."""
    out, _ = call("create_card", title="New", content="x", replace=True)
    assert out["status"] == Status.CREATED


def test_exists_changes_nothing(call):
    """Until the user agrees to a replacement, the store stays exactly as it was."""
    before = db.list_cards()
    call("create_card", title="Buy milk", content="other")
    assert db.list_cards() == before


@pytest.mark.parametrize("args", [{}, {"title": "New"}, {"content": "x"}])
def test_missing_arguments_are_errors(call, args):
    """Without both a title and content there is no card to make."""
    assert call("create_card", **args)[1] is True
    assert len(db.list_cards()) == 3


@pytest.mark.parametrize("title", ["", "   "])
def test_blank_title_is_an_error(call, title):
    """A card with no visible title could never be found by title, so it is refused."""
    msg, err = call("create_card", title=title, content="x")
    assert err and "non-empty title" in msg
    assert len(db.list_cards()) == 3
