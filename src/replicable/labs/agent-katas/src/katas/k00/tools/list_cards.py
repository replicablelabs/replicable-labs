from .. import db
from .base import tool
from .schemas import Card, Result, Status


@tool
def list_cards() -> Result:
    """List all the existing cards.

    Takes no arguments. Use it to see what cards exist, to find a card's [id]
    when you only know it exists, or after [get_card] could not find a card.

    - list all the existing cards, showing their [id] and [title]
    - only [id] and [title] are returned, not the content; use [get_card] with a returned [id] to read a full card
    - returns [status] "listed" with [cards], ordered by [id]; an empty list means there are no cards yet
    - read-only: it never changes a card
    - to search by words instead of reading the whole list, use [find_card]

    Returns:
        A `Result` (see schemas.py), which @tool serialises to the JSON string
        the model reads. Its shape is described in the bullets above, the only
        part of this docstring that the model sees.
    """
    return Result(status=Status.LISTED, cards=[Card.brief(c) for c in db.list_cards()])
