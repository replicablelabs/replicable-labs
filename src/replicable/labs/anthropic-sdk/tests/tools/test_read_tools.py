"""The read-only tools: list_cards (everything), get_card (exact), find_card (fuzzy).

Finding nothing is a normal answer; only a call that names nothing is an error.
"""

import db
from tools.schemas import Status


def test_list_cards(call):
    """The model gets an overview of every card, in id order."""
    out, err = call("list_cards")
    assert not err and out["status"] == Status.LISTED
    assert [c["id"] for c in out["cards"]] == ["1", "2", "3"]


def test_get_card(call):
    """One exact card by id or title; if both are given they must be the same card."""
    assert call("get_card", id="2")[0]["cards"][0]["title"] == "Team standup"
    assert call("get_card", title="BUY MILK")[0]["status"] == Status.FOUND
    assert call("get_card", id="99")[0]["status"] == Status.NOT_FOUND
    assert call("get_card", id="1", title="Team standup")[0]["status"] == Status.NOT_FOUND
    out, err = call("get_card")
    assert err


def test_find_card(call):
    """A loose description finds the likeliest card first, with a score; no description is
    an error.
    """
    out, err = call("find_card", content="lisbon")
    assert not err and out["status"] == Status.LISTED
    assert out["cards"][0]["title"] == "Book flights"
    assert out["cards"][0]["score"] > 0
    assert call("find_card", id="1")[0]["cards"][0]["id"] == "1"
    assert call("find_card", title="zzzzzz")[0]["cards"] == []
    assert call("find_card")[1] is True


def test_list_cards_is_brief_and_may_be_empty(call):
    """Only ids and titles are listed, and an empty store is an empty list, not an error."""
    assert call("list_cards")[0]["cards"][0] == {"id": "1", "title": "Buy milk"}
    db.store.clear()
    out, err = call("list_cards")
    assert not err and out == {"status": Status.LISTED, "cards": []}


def test_find_card_by_unknown_id_is_an_empty_list(call):
    """No card with that id is an answer, not a failure."""
    assert call("find_card", id="99") == ({"status": Status.LISTED, "cards": []}, False)


def test_find_card_puts_the_id_match_first_and_once(call):
    """A card matched by both id and words appears once, at the top, with a full score."""
    out, _ = call("find_card", id="3", content="lisbon")
    assert out["cards"] == [{"id": "3", "title": "Book flights", "score": 1.0}]

    out, _ = call("find_card", id="1", content="lisbon")
    assert [c["id"] for c in out["cards"]] == ["1", "3"]


def test_find_card_returns_at_most_six(call):
    """As its description promises: the id match plus the five best fuzzy matches."""
    for _ in range(10):
        db.add_card("Lisbon", "trip")
    assert len(call("find_card", id="1", title="lisbon")[0]["cards"]) == 6
