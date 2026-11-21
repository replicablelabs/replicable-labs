"""delete_card tool."""


def test_delete_card_tool(call):
    out, _ = call("delete_card", title="Buy milk")
    assert out["status"] == "deleted"
    assert call("delete_card", id="1")[0]["status"] == "not_found"
    assert call("delete_card")[1] is True
