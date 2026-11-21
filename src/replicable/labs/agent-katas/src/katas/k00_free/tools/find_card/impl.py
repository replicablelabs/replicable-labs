import json

from anthropic import beta_tool

from ... import db
from ...utils.utils import ToolError


@beta_tool
def find_card(id: str = "", title: str = "", content: str = "") -> str:
    """Find cards by approximate match.

    - find cards by approximate match on the card's [title] or [content], or by [id]; provide at least one
    - returns the best matches first, each with its [id], [title] and a [score] between 0 and 1; an empty list means nothing matched
    - if you know the card's [id] or its exact [title], use [get_card] instead

    Args:
        id: The card's ID.
        title: Words from the card's title.
        content: Words from the card's content.
    """
    query = " ".join(part for part in (title, content) if part)
    if not id and not query:
        raise ToolError("Provide at least one of id, title or content.")

    matches = []
    if id:
        by_id = db.get_card_by_id(id)
        if by_id is not None:
            matches.append({"id": by_id.id, "title": by_id.title, "score": 1.0})
    for card in db.fuzzy_search_cards(query) if query else []:
        if not any(m["id"] == card.id for m in matches):
            matches.append({"id": card.id, "title": card.title, "score": card.score})
    # An empty list is a normal answer, not an error.
    return json.dumps({"matches": matches})
