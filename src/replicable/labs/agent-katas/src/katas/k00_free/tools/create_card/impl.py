import json

from anthropic import beta_tool

from ... import db


@beta_tool
def create_card(title: str, content: str, replace: bool = False) -> str:
    """Create a new card.

    A card has a [title] and [content]. The card's [id] is assigned
    automatically, so never provide one.

    - create a new card by providing the card's [title] and the card's [content]
    - titles are unique, ignoring letter case: if a card with that [title] already exists nothing is changed and the result has status "exists"
    - when the status is "exists", show the user the existing card and ask whether it should be replaced; only if they agree, call this tool again with the same [title] and [content] and [replace] set to true
    - never set [replace] to true without the user's agreement: replacing overwrites the existing card's content (the card keeps its [id])
    - writes data: creating adds a card, replacing overwrites one
    - returns status "created", "exists" or "replaced", each with the card ([id], [title], [content])
    - a missing [title] or [content] produces an error result; call again with both
    - examples: [title] "Capital of France" with [content] "Paris"; then, after the user agreed to replace it, the same [title] with new [content] and [replace] true

    Args:
        title: The card's name. Must be non-empty.
        content: The card's content.
        replace: Set to true only after the user agreed to replace the existing card with this title.

    Returns:
        A JSON string. Its shape is described in the bullets above, which are
        the only part of this docstring the model sees besides Args.
    """
    existing = db.get_card_by_title(title)
    if existing is None:
        card = db.add_card(title, content)
        return json.dumps({"status": "created", "card": card.to_dict()})
    if not replace:
        # Not an error: the model must ask the user, then call again with replace=true.
        return json.dumps({"status": "exists", "card": existing.to_dict()})
    card = db.update_card(existing.id, content)
    return json.dumps({"status": "replaced", "card": card.to_dict()})
