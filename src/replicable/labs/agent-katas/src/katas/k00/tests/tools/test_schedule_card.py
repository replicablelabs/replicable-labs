"""schedule_card tool."""


def test_schedule_card(call):
    out, _ = call("schedule_card", id="1", scheduled_at="2026-11-25T09:00")
    assert out["status"] == "scheduled" and out["card"]["scheduled_at"] == "2026-11-25T09:00:00"
    assert call("get_card", id="1")[0]["card"]["scheduled_at"] == "2026-11-25T09:00:00"
    assert call("schedule_card", id="99", scheduled_at="2026-11-25")[0]["status"] == "not_found"
    msg, err = call("schedule_card", id="1", scheduled_at="next tuesday")
    assert err and "ISO 8601" in msg
