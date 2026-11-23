"""create_card: created / exists / replaced."""

from tools.schemas import Status


def test_create_card_flow(call):
    """Create a card, hit the duplicate-title case, then replace its content."""
    out, _ = call("create_card", title="Capital of France", content="Paris")
    assert out["status"] == Status.CREATED and out["cards"][0]["id"] == "4"

    out, _ = call("create_card", title="capital of france", content="Lyon")
    assert out["status"] == Status.EXISTS and out["cards"][0]["content"] == "Paris"

    out, _ = call("create_card", title="Capital of France", content="Lyon", replace=True)
    assert out["status"] == Status.REPLACED and out["cards"][0]["id"] == "4"
    assert call("get_card", id="4")[0]["cards"][0]["content"] == "Lyon"
