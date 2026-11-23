"""Data types for the card store."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class Card:
    id: str
    title: str
    content: str
    # ISO 8601 datetime the card is scheduled for study; None if unscheduled.
    scheduled_at: Optional[str] = None
    # Only set by fuzzy_search_cards; None for every other lookup.
    score: Optional[float] = None

    def to_dict(self) -> dict:
        """Plain dict without the None fields (compact, JSON-serializable)."""
        return {k: v for k, v in asdict(self).items() if v is not None}
