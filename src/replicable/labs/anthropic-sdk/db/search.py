"""Searching cards: substring and fuzzy ranking."""

from __future__ import annotations

import difflib
import re
from dataclasses import replace

from . import store
from .models import Card


def search_cards(query: str) -> list[Card]:
    """Return cards whose content contains the query (case-insensitive)."""
    needle = query.casefold()
    return [c for c in store.list_cards() if needle in c.content.casefold()]


def _words(text: str) -> list[str]:
    """Split text into lowercase word tokens."""
    return re.findall(r"\w+", text.casefold())


def _word_score(query_word: str, text_words: list[str]) -> float:
    """Best similarity (0-1) between one query word and any word in the text."""
    best = 0.0
    for word in text_words:
        if query_word in word:
            return 1.0
        best = max(best, difflib.SequenceMatcher(None, query_word, word).ratio())
    return best


def fuzzy_search_cards(
    query: str, limit: int = 5, threshold: float = 0.6
) -> list[Card]:
    """Rank cards by how well their title and content match the query.

    Each query word is scored against the best-matching word in the card
    (exact or substring = 1.0, otherwise difflib similarity), and a card's
    score is the average over the query words. Returns up to `limit` cards
    scoring at least `threshold`, best first. Each returned card has its
    `score` field set.
    """
    query_words = _words(query)
    if not query_words:
        return []

    results: list[Card] = []
    for card in store.list_cards():
        text_words = _words(card.title + " " + card.content)
        score = sum(_word_score(q, text_words) for q in query_words) / len(query_words)
        if score >= threshold:
            results.append(replace(card, score=round(score, 2)))

    results.sort(key=lambda c: c.score, reverse=True)
    return results[:limit]
