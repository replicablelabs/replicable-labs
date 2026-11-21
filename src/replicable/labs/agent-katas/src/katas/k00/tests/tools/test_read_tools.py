"""The read-only tools: list_cards, get_card, find_card."""


def test_list_cards(call):
    out, err = call("list_cards")
    assert not err and [c["id"] for c in out["cards"]] == ["1", "2", "3"]


def test_get_card(call):
    assert call("get_card", id="2")[0]["card"]["title"] == "Team standup"
    assert call("get_card", title="BUY MILK")[0]["status"] == "found"
    assert call("get_card", id="99")[0]["status"] == "not_found"
    assert call("get_card", id="1", title="Team standup")[0]["status"] == "not_found"
    out, err = call("get_card")
    assert err


def test_find_card(call):
    out, err = call("find_card", content="lisbon")
    assert not err and out["cards"][0]["title"] == "Book flights"
    assert out["cards"][0]["score"] > 0
    assert call("find_card", id="1")[0]["cards"][0]["id"] == "1"
    assert call("find_card", title="zzzzzz")[0]["cards"] == []
    assert call("find_card")[1] is True
