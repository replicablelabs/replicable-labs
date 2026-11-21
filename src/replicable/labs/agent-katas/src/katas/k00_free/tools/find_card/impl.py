import json

from anthropic import beta_tool

from ... import db
from ...utils.utils import ToolError


@beta_tool
def find_card(id: str = "", title: str = "", content: str = "") -> str:
    """Find cards by approximate match.

    Use it when you don't know the exact [id] or [title], for example when the
    user describes a card loosely or misspells its title.

    - find cards by approximate match on the card's [title] or [content], or by [id]; provide at least one
    - matching is fuzzy: each word you give is compared with the words of every card's title and content, so typos and partial words still match
    - returns [matches], the best first, each with its [id], [title] and a [score] between 0 and 1 (higher is a better match); only a short list is returned (at most 6)
    - only [id], [title] and [score] are returned, not the content; use [get_card] with a returned [id] to read the full card
    - an empty list means nothing matched; that is a normal answer, not an error, so tell the user or try different words, or use [list_cards]
    - read-only: it never changes a card
    - if you know the card's [id] or its exact [title], use [get_card] instead
    - an error result means none of [id], [title] or [content] was given; call again with at least one
    - examples: [content] "lisbon"; [title] "standup" ; [title] "bok flights" (typo still matches "Book flights")

    Args:
        id: The card's ID. If a card has this ID it is returned first with a score of 1.
        title: Words from the card's title.
        content: Words from the card's content.

    Returns:
        A JSON string. Its shape is described in the bullets above, which are
        the only part of this docstring the model sees besides Args.

    Raises:
        ToolError: None of id, title or content was given. run_tool turns it
            into an is_error tool_result.
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
