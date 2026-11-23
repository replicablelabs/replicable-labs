"""delete_card tool."""

from k00.tools.schemas import Status


def test_delete_card_tool(call):
    """Delete by title, then a missing id is `not_found` and no arguments is an error."""
    out, _ = call("delete_card", title="Buy milk")
    assert out["status"] == Status.DELETED
    assert call("delete_card", id="1")[0]["status"] == Status.NOT_FOUND
    assert call("delete_card")[1] is True
