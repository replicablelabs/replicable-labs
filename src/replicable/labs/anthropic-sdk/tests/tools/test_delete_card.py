"""delete_card: there is no undo, so it deletes only when the card is unambiguous."""

import db
from tools.schemas import Status


def test_delete_card_tool(call):
    """A named card is removed. Asking for it again is a normal `not_found`, while naming no
    card at all is a mistake the model must fix.
    """
    out, _ = call("delete_card", title="Buy milk")
    assert out["status"] == Status.DELETED
    assert call("delete_card", id="1")[0]["status"] == Status.NOT_FOUND
    assert call("delete_card")[1] is True


def test_disagreeing_id_and_title_delete_nothing(call):
    """If the id and the title name different cards, neither is touched."""
    assert call("delete_card", id="1", title="Team standup")[0]["status"] == Status.NOT_FOUND
    assert len(db.list_cards()) == 3


def test_result_is_brief(call):
    """The model is told which card went, without its content."""
    assert call("delete_card", id="1")[0]["cards"] == [{"id": "1", "title": "Buy milk"}]
