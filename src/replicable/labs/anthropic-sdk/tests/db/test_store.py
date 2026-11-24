"""The card store: seeding, ids, lookups, updates, schedules, reset and delete."""

import pytest

import db


def test_seed_and_ids():
    """A run starts with the three sample cards, and a new card takes the next number."""
    assert [c.id for c in db.list_cards()] == ["1", "2", "3"]
    assert db.add_card("New", "x").id == "4"


def test_reset_restarts_ids():
    """After a reset it is as if nothing had been added: same cards, same numbering."""
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
    """Delete by id, title or both. When the two disagree it is unclear which card is meant,
    so nothing is deleted.
    """
    before = len(db.list_cards())
    deleted = db.delete_card(id, title)
    assert (deleted.id if deleted else None) == expect_deleted
    assert len(db.list_cards()) == before - (1 if expect_deleted else 0)


def test_ids_are_not_reused_after_a_delete():
    """An old id never comes to mean a different card."""
    db.delete_card("3")
    assert db.add_card("New", "x").id == "4"


def test_cards_are_listed_in_numeric_order():
    """Card 10 comes after card 9, not after card 1 as it would in text order."""
    for i in range(8):
        db.add_card(f"Card {i}", "x")
    assert [c.id for c in db.list_cards()] == [str(i) for i in range(1, 12)]


@pytest.mark.parametrize(
    "id,title,expected",
    [
        (None, None, None),
        ("2", None, "2"),
        (None, "TEAM STANDUP", "2"),
        (None, "Team", None),
        ("2", "team standup", "2"),
        ("2", "Buy milk", None),
        ("99", "Buy milk", None),
        ("1", "nope", None),
    ],
)
def test_find_card(id, title, expected):
    """Titles ignore case but must be complete; an id and a title must agree."""
    card = db.find_card(id, title)
    assert (card.id if card else None) == expected


def test_first_of_two_cards_with_one_title_wins():
    """The store allows duplicate titles; a lookup gives the oldest card."""
    db.add_card("buy milk", "another")
    assert db.get_card_by_title("Buy milk").id == "1"


def test_update_changes_only_the_content():
    """The id, title and schedule of an updated card stay as they were."""
    db.set_schedule("1", "2026-11-25T09:00:00")
    card = db.update_card("1", "new")
    assert card == db.get_card_by_id("1")
    assert card == db.Card("1", "Buy milk", "new", scheduled_at="2026-11-25T09:00:00")


def test_schedule_changes_only_the_schedule():
    """Scheduling keeps the card's text, and scheduling again replaces the old time."""
    before = db.get_card_by_id("1")
    db.set_schedule("1", "2026-11-25T09:00:00")
    card = db.set_schedule("1", "2026-12-01T00:00:00")
    assert card == db.get_card_by_id("1")
    assert card.scheduled_at == "2026-12-01T00:00:00"
    assert (card.title, card.content) == (before.title, before.content)


def test_changing_a_missing_card_does_nothing():
    """Updating or scheduling an unknown id returns None and creates no card."""
    assert db.update_card("99", "x") is None
    assert db.set_schedule("99", "2026-11-25") is None
    assert len(db.list_cards()) == 3
