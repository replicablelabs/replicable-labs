import json

from anthropic import beta_tool

from ... import db
from ...utils.utils import ToolError


@beta_tool
def delete_card(id: str = "", title: str = "") -> str:
    """Delete a card.

    - Delete a card by [id] or by [title]; provide at least one, and if you provide both they must belong to the same card
    - Get the card with [get_card] for exact matches, otherwise follow the instructions at [get_card] to get the card
    - If no such card exists, inform the user that no such card exists
    - List existing cards if they **sort of match** the user selected card by [title], if any cards exist. You can find these cards by running [list_cards].

    Args:
        id: The card's UID.
        title: The card's name.
    """
    if not id and not title:
        raise ToolError("Provide the card's id or title.")
    card = db.delete_card(id, title)
    if card is None:
        return json.dumps(
            {
                "status": "not_found",
                "message": "No card matches. If both id and title are given they must refer to the same card.",
            }
        )
    return json.dumps({"status": "deleted", "card": {"id": card.id, "title": card.title}})
