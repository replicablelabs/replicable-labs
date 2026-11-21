import json

from anthropic import beta_tool

from ... import db


@beta_tool
def list_cards() -> str:
    """List all the existing cards.

    Takes no arguments. Use it to see what cards exist, to find a card's [id]
    when you only know it exists, or after [get_card] could not find a card.

    - list all the existing cards, showing their [id] and [title]
    - only [id] and [title] are returned, not the content; use [get_card] with a returned [id] to read a full card
    - returns [cards], ordered by [id]; an empty list means there are no cards yet
    - read-only: it never changes a card
    - to search by words instead of reading the whole list, use [find_card]

    Returns:
        A JSON string. Its shape is described in the bullets above, which are
        the only part of this docstring the model sees.
    """
    return json.dumps({"cards": [{"id": c.id, "title": c.title} for c in db.list_cards()]})
