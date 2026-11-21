"""The contract for what card tools return.

Every tool returns one of these models; `base.py` serialises it to the
JSON string the model reads. Statuses and field names are defined only here,
so tools cannot drift apart. The descriptions in each tool's docstring say what
the model should do for each status.

`Card` here is the card as the model sees it; `db.Card` is the stored one.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from .. import db

Status = Literal[
    "created",    # create_card: a new card was added
    "exists",     # create_card: title already taken, nothing changed
    "replaced",   # create_card: existing card's content was overwritten
    "found",      # get_card
    "deleted",    # delete_card
    "scheduled",  # schedule_card
    "not_found",  # get/delete/schedule: no card matches (a normal answer, not an error)
]

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
    """Outcome of a tool that acts on one card."""

    status: Status
    card: Optional[Card] = None
    message: Optional[str] = None

    @classmethod
    def not_found(cls) -> "Result":
        """The `not_found` outcome, with the standard message about id and title."""
        return cls(status="not_found", message=NO_MATCH)


class CardList(BaseModel):
    """A list of cards: find_card (best first, with scores) or list_cards (by id).

    An empty list is a normal answer, not an error.
    """

    cards: list[Card]
