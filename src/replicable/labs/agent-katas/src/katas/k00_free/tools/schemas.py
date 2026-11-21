"""The contract for what card tools return.

Every tool returns one of these models; `base.py` serialises it to the
JSON string the model reads. Statuses and field names are defined only here,
so tools cannot drift apart. The descriptions in each tool's docstring say what
the model should do for each status.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from ..db import Card

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


class CardView(BaseModel):
    """A card as shown to the model. Unset fields are left out of the JSON."""

    id: str
    title: str
    content: Optional[str] = None
    scheduled_at: Optional[str] = None

    @classmethod
    def full(cls, card: Card) -> "CardView":
        return cls(id=card.id, title=card.title, content=card.content, scheduled_at=card.scheduled_at)

    @classmethod
    def brief(cls, card: Card) -> "CardView":
        return cls(id=card.id, title=card.title)


class Result(BaseModel):
    """Outcome of a tool that acts on one card."""

    status: Status
    card: Optional[CardView] = None
    message: Optional[str] = None

    @classmethod
    def not_found(cls) -> "Result":
        return cls(status="not_found", message=NO_MATCH)


class Match(BaseModel):
    id: str
    title: str
    score: float


class Matches(BaseModel):
    """find_card: best matches first; an empty list is a normal answer."""

    matches: list[Match]


class Cards(BaseModel):
    """list_cards: every card ordered by id; an empty list means there are none."""

    cards: list[CardView]
