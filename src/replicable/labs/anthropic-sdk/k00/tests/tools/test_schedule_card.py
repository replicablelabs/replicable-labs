"""schedule_card tool."""

from k00.tools.schemas import Status


def test_schedule_card(call):
    """Schedule a card with an ISO 8601 time; a bad time is an error and a missing id is `not_found`."""
    out, _ = call("schedule_card", id="1", scheduled_at="2026-11-25T09:00")
    assert out["status"] == Status.SCHEDULED and out["cards"][0]["scheduled_at"] == "2026-11-25T09:00:00"
    assert call("get_card", id="1")[0]["cards"][0]["scheduled_at"] == "2026-11-25T09:00:00"
    assert call("schedule_card", id="99", scheduled_at="2026-11-25")[0]["status"] == Status.NOT_FOUND
    msg, err = call("schedule_card", id="1", scheduled_at="next tuesday")
    assert err and "ISO 8601" in msg
