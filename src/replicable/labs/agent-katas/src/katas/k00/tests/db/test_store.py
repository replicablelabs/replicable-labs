"""The card store: seeding, ids, reset, delete."""

import pytest

from katas.k00 import db


def test_seed_and_ids():
    assert [c.id for c in db.list_cards()] == ["1", "2", "3"]
    assert db.add_card("New", "x").id == "4"


def test_reset_restarts_ids():
    db.add_card("New", "x")
    db.reset()
    assert [c.id for c in db.list_cards()] == ["1", "2", "3"]


@pytest.mark.parametrize(
    "id,title,expect_deleted",
    [
        (None, None, None),
        ("99", None, None),
        (None, "nope", None),
        ("1", "Team standup", None),   # id and title point at different cards
        ("1", "buy milk", "1"),
        (None, "Team standup", "2"),
        ("3", None, "3"),
    ],
)
def test_delete_card(id, title, expect_deleted):
    before = len(db.list_cards())
    deleted = db.delete_card(id, title)
    assert (deleted.id if deleted else None) == expect_deleted
    assert len(db.list_cards()) == before - (1 if expect_deleted else 0)
