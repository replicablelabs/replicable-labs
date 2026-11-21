"""The contract for what card tools return.

Every tool returns a `Result`; `base.py` serialises it to the JSON string
the model reads. Statuses and field names are defined only here,
so tools cannot drift apart. The descriptions in each tool's docstring say what
the model should do for each status.

`Card` here is the card as the model sees it; `db.Card` is the stored one.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from .. import db

class Status(StrEnum):
    """Every status a tool result can carry. The value is what the model sees in the JSON.

    A `StrEnum` member is also a plain string, so `Status.CREATED == "created"`.
    """

    CREATED = "created"      # create_card: a new card was added
    EXISTS = "exists"        # create_card: title already taken, nothing changed
    REPLACED = "replaced"    # create_card: existing card's content was overwritten
    FOUND = "found"          # get_card
    DELETED = "deleted"      # delete_card
    SCHEDULED = "scheduled"  # schedule_card
    LISTED = "listed"        # find_card, list_cards: the cards in the result (possibly none)
    NOT_FOUND = "not_found"  # get/delete/schedule: no card matches (a normal answer, not an error)

NO_MATCH = "No card matches. If both id and title are given they must refer to the same card."


class Card(BaseModel):
    """A card as shown to the model. Unset fields are left out of the JSON."""

    id: str
    title: str
    content: Optional[str] = None
    scheduled_at: Optional[str] = None
    score: Optional[float] = None  # only on find_card results

    @classmethod
    def full(cls, card: db.Card) -> "Card":
        """The card with every stored field (id, title, content, scheduled_at)."""
        return cls(id=card.id, title=card.title, content=card.content, scheduled_at=card.scheduled_at)

    @classmethod
    def brief(cls, card: db.Card) -> "Card":
        """Just the id and title, for results that don't need the content."""
        return cls(id=card.id, title=card.title)


class Result(BaseModel):
    """What every tool returns: a status, the cards involved and an optional message.

    `cards` is always a list: empty, one card, or several (an empty list is a
    normal answer, not an error). Which it is follows from the status.
    """

    status: Status
    cards: list[Card] = Field(default_factory=list)
    message: Optional[str] = None

    @classmethod
    def not_found(cls) -> "Result":
        """The `not_found` outcome, with the standard message about id and title."""
        return cls(status=Status.NOT_FOUND, message=NO_MATCH)
