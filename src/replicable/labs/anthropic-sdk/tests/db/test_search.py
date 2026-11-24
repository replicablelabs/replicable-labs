"""Searching the store: exact substring search and typo-tolerant fuzzy search."""

import pytest


import db


def test_fuzzy_search_ranks_and_scores():
    """The closest card comes first and says how close it is; no words means no matches."""
    hits = db.fuzzy_search_cards("lisbon flights")
    assert hits[0].title == "Book flights" and hits[0].score is not None
    assert db.fuzzy_search_cards("") == []


@pytest.mark.parametrize(
    "query,ids",
    [("LISBON", ["3"]), ("standup", ["2"]), ("th", ["1", "3"]), ("Buy milk", []), ("zzz", [])],
)
def test_substring_search_looks_in_content_only(query, ids):
    """Letter case is ignored, and a title alone is not a match."""
    assert [c.id for c in db.search_cards(query)] == ids


def test_fuzzy_search_forgives_typos():
    """A misspelt word still finds the card, with a score a little below perfect."""
    hit = db.fuzzy_search_cards("flihgts")[0]
    assert hit.id == "3" and 0.6 <= hit.score < 1


def test_fuzzy_score_is_the_average_over_the_words():
    """One word that matches and one that shares no letters give half a point."""
    (hit,) = db.fuzzy_search_cards("lisbon 777", threshold=0.5)
    assert hit.id == "3" and hit.score == 0.5


def test_fuzzy_search_ignores_punctuation_only_queries():
    """Punctuation holds no words to look for, so it matches nothing."""
    assert db.fuzzy_search_cards("?!") == []


def test_fuzzy_search_returns_at_most_limit_best_first():
    """A long list of matches is cut after the best ones."""
    for _ in range(10):
        db.add_card("Lisbon", "trip")
    assert len(db.fuzzy_search_cards("lisbon")) == 5
    scores = [c.score for c in db.fuzzy_search_cards("lisbon milk", limit=20, threshold=0)]
    assert len(scores) == 13 and scores == sorted(scores, reverse=True)


def test_fuzzy_search_does_not_write_scores_to_the_store():
    """A score belongs to one search, so the stored card stays unscored."""
    db.fuzzy_search_cards("lisbon")
    assert all(c.score is None for c in db.list_cards())
