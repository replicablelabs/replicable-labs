"""The read-only tools: list_cards, get_card, find_card."""

from k00.tools.schemas import Status


def test_list_cards(call):
    """list_cards returns every card ordered by id."""
    out, err = call("list_cards")
    assert not err and out["status"] == Status.LISTED
    assert [c["id"] for c in out["cards"]] == ["1", "2", "3"]


def test_get_card(call):
    """get_card finds by id or title, and id plus title must agree."""
    assert call("get_card", id="2")[0]["cards"][0]["title"] == "Team standup"
    assert call("get_card", title="BUY MILK")[0]["status"] == Status.FOUND
    assert call("get_card", id="99")[0]["status"] == Status.NOT_FOUND
    assert call("get_card", id="1", title="Team standup")[0]["status"] == Status.NOT_FOUND
    out, err = call("get_card")
    assert err


def test_find_card(call):
    """find_card ranks fuzzy matches with scores and needs at least one criterion."""
    out, err = call("find_card", content="lisbon")
    assert not err and out["status"] == Status.LISTED
    assert out["cards"][0]["title"] == "Book flights"
    assert out["cards"][0]["score"] > 0
    assert call("find_card", id="1")[0]["cards"][0]["id"] == "1"
    assert call("find_card", title="zzzzzz")[0]["cards"] == []
    assert call("find_card")[1] is True
