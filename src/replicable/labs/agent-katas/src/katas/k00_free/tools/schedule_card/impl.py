from datetime import datetime

from ... import db
from ...results import CardView, Result
from ...utils.utils import ToolError
from ..base import tool


@tool
def schedule_card(scheduled_at: str, id: str = "", title: str = "") -> Result:
    """Schedule a card for study.

    Sets the date and time at which the user should study the card.

    - find the card by [id] or by [title]; provide at least one, and if you provide both they must belong to the same card
    - assign a datetime to the card by providing [scheduled_at] in ISO 8601 format, e.g. 2026-11-25T09:00 (no timezone means the user's local time)
    - convert relative wording such as "tomorrow at 9" into an absolute datetime first; if you don't know today's date, ask the user instead of guessing
    - a card has one schedule: scheduling it again replaces its previous datetime
    - writes data: it changes only the card's schedule, never its title or content
    - returns status "scheduled" with the card's [id], [title] and [scheduled_at], or status "not_found" with a message; not found is a normal answer, not an error
    - an error result means no [id] or [title] was given, or [scheduled_at] is not a valid ISO 8601 datetime; fix the argument and call again
    - examples: [id] "1" with [scheduled_at] "2026-11-25T09:00"; [title] "Buy milk" with [scheduled_at] "2026-12-01"

    Args:
        scheduled_at: When to study the card, ISO 8601, e.g. 2026-11-25T09:00.
        id: The card's UID.
        title: The card's title. Case-insensitive, otherwise exact.

    Returns:
        A `Result` (see results.py), which @tool serialises to the JSON string
        the model reads. Its shape is described in the bullets above, the only
        part of this docstring besides Args that the model sees.

    Raises:
        ToolError: Neither id nor title was given, or scheduled_at is not an
            ISO 8601 datetime. run_tool turns it into an is_error tool_result.
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
        return Result.not_found()
    card = db.set_schedule(card.id, when.isoformat())
    return Result(
        status="scheduled",
        card=CardView(id=card.id, title=card.title, scheduled_at=card.scheduled_at),
    )
