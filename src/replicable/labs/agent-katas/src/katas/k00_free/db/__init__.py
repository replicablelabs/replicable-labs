"""In-memory card store for the k00 exercise.

Lives for the lifetime of the Python process. Each `kata run` starts fresh,
so the seed cards are restored every time.

Layout:
    models.py  the Card dataclass
    store.py   create / read / update / delete
    search.py  substring and fuzzy search
    seed.py    sample cards

Every function returns `Card` objects (or None / lists of them), never dicts.
Tools import this package as `db` and call the names re-exported below.
"""

from . import search, seed, store
from .models import Card
from .search import fuzzy_search_cards, search_cards
from .store import (
    add_card,
    delete_card,
    find_card,
    get_card_by_id,
    get_card_by_title,
    list_cards,
    set_schedule,
    update_card,
)


def reset() -> None:
    """Drop every card and reload the seed cards (used by tests)."""
    store.clear()
    seed.seed()


seed.seed()

__all__ = [
    "Card",
    "add_card",
    "delete_card",
    "find_card",
    "fuzzy_search_cards",
    "get_card_by_id",
    "get_card_by_title",
    "list_cards",
    "reset",
    "search",
    "search_cards",
    "seed",
    "set_schedule",
    "store",
    "update_card",
]
