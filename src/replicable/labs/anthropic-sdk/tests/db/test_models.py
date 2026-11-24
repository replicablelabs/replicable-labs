"""The stored `Card`: an immutable record that can be turned into a dict."""

from dataclasses import FrozenInstanceError

import pytest

from db import Card


def test_to_dict_leaves_out_unset_fields():
    """An unscheduled, unscored card has no empty `scheduled_at` or `score` keys."""
    assert Card("1", "A", "x").to_dict() == {"id": "1", "title": "A", "content": "x"}


def test_to_dict_keeps_falsy_values_that_were_set():
    """Only None means "not set": a score of 0 and empty content are real values."""
    card = Card("1", "A", "", scheduled_at="2026-11-25", score=0.0)
    assert card.to_dict() == {
        "id": "1", "title": "A", "content": "", "scheduled_at": "2026-11-25", "score": 0.0,
    }


def test_cards_cannot_be_edited_in_place():
    """Whoever holds a card cannot change the store behind its back."""
    with pytest.raises(FrozenInstanceError):
        Card("1", "A", "x").title = "B"
