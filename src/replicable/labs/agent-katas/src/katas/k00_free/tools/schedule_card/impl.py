from datetime import datetime

from ... import db
from ...utils.utils import ToolError


def schedule_card(scheduled_at, id=None, title=None):
    if not id and not title:
        raise ToolError("Provide the card's id or title.")
    try:
        when = datetime.fromisoformat(scheduled_at)
    except (TypeError, ValueError):
        raise ToolError(
            f"scheduled_at {scheduled_at!r} is not an ISO 8601 datetime, e.g. 2026-11-25T09:00."
        )

    card = db.find_card(id, title)
    if card is None:
        return {
            "status": "not_found",
            "message": "No card matches. If both id and title are given they must refer to the same card.",
        }
    card = db.set_schedule(card.id, when.isoformat())
    return {
        "status": "scheduled",
        "card": {"id": card.id, "title": card.title, "scheduled_at": card.scheduled_at},
    }
