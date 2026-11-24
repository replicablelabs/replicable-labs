"""schedule_card: give a card a study time, written as an ISO 8601 date and time."""

import pytest

import db
from tools.schemas import Status


def test_schedule_card(call):
    """A clear time is stored on the card. Vague wording is an error the model must fix, and
    an unknown card is a normal `not_found`.
    """
    out, _ = call("schedule_card", id="1", scheduled_at="2026-11-25T09:00")
    assert out["status"] == Status.SCHEDULED and out["cards"][0]["scheduled_at"] == "2026-11-25T09:00:00"
    assert call("get_card", id="1")[0]["cards"][0]["scheduled_at"] == "2026-11-25T09:00:00"
    assert call("schedule_card", id="99", scheduled_at="2026-11-25")[0]["status"] == Status.NOT_FOUND
    msg, err = call("schedule_card", id="1", scheduled_at="next tuesday")
    assert err and "ISO 8601" in msg


def test_scheduling_without_a_card_is_an_error(call):
    """A time alone does not say which card to schedule."""
    msg, err = call("schedule_card", scheduled_at="2026-11-25T09:00")
    assert err and "id or title" in msg


@pytest.mark.parametrize(
    "given,stored",
    [
        ("2026-12-01", "2026-12-01T00:00:00"),
        ("2026-12-01T09:00+01:00", "2026-12-01T09:00:00+01:00"),
    ],
)
def test_times_are_stored_in_one_format(call, given, stored):
    """A bare date means midnight, and a timezone is kept when given."""
    out, _ = call("schedule_card", title="buy milk", scheduled_at=given)
    assert out["cards"] == [{"id": "1", "title": "Buy milk", "scheduled_at": stored}]


def test_a_bad_time_keeps_the_old_schedule(call):
    """A failed call leaves the card as it was."""
    call("schedule_card", id="1", scheduled_at="2026-12-01")
    call("schedule_card", id="1", scheduled_at="soon")
    assert db.get_card_by_id("1").scheduled_at == "2026-12-01T00:00:00"
