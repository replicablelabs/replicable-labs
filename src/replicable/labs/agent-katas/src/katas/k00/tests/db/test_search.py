"""Fuzzy card search."""

from katas.k00 import db


def test_fuzzy_search_ranks_and_scores():
    hits = db.fuzzy_search_cards("lisbon flights")
    assert hits[0].title == "Book flights" and hits[0].score is not None
    assert db.fuzzy_search_cards("") == []
