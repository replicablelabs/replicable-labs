"""In-memory card storage: create, read, update, delete.

State lives for the lifetime of the Python process.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from typing import Optional

from .models import Card

_cards: dict[str, Card] = {}
_ids = itertools.count(1)


def clear() -> None:
    """Remove every card and restart ID numbering at 1."""
    global _ids
    _cards.clear()
    _ids = itertools.count(1)


def add_card(title: str, content: str) -> Card:
    """Create a card with a new ID, store it and return it."""
    card = Card(id=str(next(_ids)), title=title, content=content)
    _cards[card.id] = card
    return card


def list_cards() -> list[Card]:
    """Return every card, ordered by ID."""
    return sorted(_cards.values(), key=lambda c: int(c.id))


def get_card_by_id(id: str) -> Optional[Card]:
    """Return the card with this ID, or None."""
    return _cards.get(id)


def get_card_by_title(title: str) -> Optional[Card]:
    """Return the first card whose title matches (case-insensitive), or None."""
    wanted = title.casefold()
    for card in list_cards():
        if card.title.casefold() == wanted:
            return card
    return None


def find_card(id: Optional[str] = None, title: Optional[str] = None) -> Optional[Card]:
    """Resolve a card by ID and/or title.

    Returns None if neither is given, nothing matches, or both are given but
    point at different cards.
    """
    card_by_id = get_card_by_id(id) if id else None
    card_by_title = get_card_by_title(title) if title else None

    if id and title:
        if card_by_id is None or card_by_title is None:
            return None
        if card_by_id.id != card_by_title.id:
            return None

    return card_by_id or card_by_title


def update_card(id: str, content: str) -> Optional[Card]:
    """Replace the content of an existing card (ID and title are kept)."""
    card = _cards.get(id)
    if card is None:
        return None
    _cards[id] = replace(card, content=content)
    return _cards[id]


def set_schedule(id: str, scheduled_at: str) -> Optional[Card]:
    """Set the study datetime (ISO 8601 string) of a card; None if no such card."""
    card = _cards.get(id)
    if card is None:
        return None
    _cards[id] = replace(card, scheduled_at=scheduled_at)
    return _cards[id]


def delete_card(id: Optional[str] = None, title: Optional[str] = None) -> Optional[Card]:
    """Delete a card by ID and/or title and return the deleted card.

    Returns None, deleting nothing, if neither is given, no card matches, or
    both are given but point at different cards.
    """
    card = find_card(id, title)
    if card is None:
        return None
    return _cards.pop(card.id)
