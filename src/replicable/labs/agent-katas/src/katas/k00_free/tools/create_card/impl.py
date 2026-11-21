import json

from anthropic import beta_tool

from ... import db


@beta_tool
def create_card(title: str, content: str, replace: bool = False) -> str:
    """Create a new card.

    - create a new card by providing the card's [title] and the card's [content]
    - if there is a card with that [title] already, the result has status "exists" and nothing is changed: ask the user whether the existing card should be replaced
    - if the user agrees, call this tool again with the same [title] and [content] and [replace] set to true

    Args:
        title: The card's name.
        content: The card's content.
        replace: Set to true only after the user agreed to replace the existing card with this title.
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
