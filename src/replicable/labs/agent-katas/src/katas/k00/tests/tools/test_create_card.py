"""create_card: created / exists / replaced."""


def test_create_card_flow(call):
    out, _ = call("create_card", title="Capital of France", content="Paris")
    assert out["status"] == "created" and out["card"]["id"] == "4"

    out, _ = call("create_card", title="capital of france", content="Lyon")
    assert out["status"] == "exists" and out["card"]["content"] == "Paris"

    out, _ = call("create_card", title="Capital of France", content="Lyon", replace=True)
    assert out["status"] == "replaced" and out["card"]["id"] == "4"
    assert call("get_card", id="4")[0]["card"]["content"] == "Lyon"
