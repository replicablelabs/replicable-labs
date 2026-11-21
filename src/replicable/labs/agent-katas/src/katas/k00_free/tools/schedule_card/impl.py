import json
from datetime import datetime

from anthropic import beta_tool

from ... import db
from ...utils.utils import ToolError


@beta_tool
def schedule_card(scheduled_at: str, id: str = "", title: str = "") -> str:
    """Schedule a card for study.

    - find the card by [id] or by [title]; provide at least one, and if you provide both they must belong to the same card
    - assign a datetime to the card by providing [scheduled_at] in ISO 8601 format, e.g. 2026-11-25T09:00
    - scheduling a card again replaces its previous datetime

    Args:
        scheduled_at: When to study the card, ISO 8601, e.g. 2026-11-25T09:00.
        id: The card's UID.
        title: The card's name.
    """
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
        return json.dumps(
            {
                "status": "not_found",
                "message": "No card matches. If both id and title are given they must refer to the same card.",
            }
        )
    card = db.set_schedule(card.id, when.isoformat())
    return json.dumps(
        {
            "status": "scheduled",
            "card": {"id": card.id, "title": card.title, "scheduled_at": card.scheduled_at},
        }
    )
