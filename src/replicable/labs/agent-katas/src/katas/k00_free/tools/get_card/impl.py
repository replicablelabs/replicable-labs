import json

from anthropic import beta_tool

from ... import db
from ...utils.utils import ToolError


@beta_tool
def get_card(id: str = "", title: str = "") -> str:
    """Get one card by its exact id or exact title.

    - get card based on a [title] or on an [id]; provide at least one, and if you provide both they must belong to the same card
    - use [list_cards] if you couldn't find a card with that [title] or [id]
    - matches are **exact matches**
    - you can also use [find_card] if you couldn't find exact matches

    Args:
        id: The card's UID.
        title: The card's name.
    """
    if not id and not title:
        raise ToolError("Provide the card's id or title.")
    card = db.find_card(id, title)
    if card is None:
        return json.dumps(
            {
                "status": "not_found",
                "message": "No card matches. If both id and title are given they must refer to the same card.",
            }
        )
    return json.dumps({"status": "found", "card": card.to_dict()})
