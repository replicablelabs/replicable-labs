"""Sample cards loaded when the db package is imported."""

from __future__ import annotations

from . import store

SAMPLES = [
    ("Buy milk", "Pick up two litres of semi-skimmed milk on the way home."),
    ("Team standup", "Daily 9:30 standup. Share yesterday, today and blockers."),
    ("Book flights", "Flights to Lisbon for the conference, economy, window seat."),
]


def seed() -> None:
    """Add the sample cards to the store."""
    for title, content in SAMPLES:
        store.add_card(title, content)
