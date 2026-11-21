import json

from anthropic import beta_tool

from ... import db
from ...utils.utils import ToolError


@beta_tool
def delete_card(id: str = "", title: str = "") -> str:
    """Delete a card permanently.

    There is no undo. Be sure which card the user means before calling it.

    - delete a card by [id] or by [title]; provide at least one, and if you provide both they must belong to the same card
    - get the card with [get_card] for exact matches, otherwise follow the instructions at [get_card] to get the card
    - if the user described the card loosely, use [find_card] or [list_cards] to identify it first, and confirm with the user when more than one card could match
    - if no such card exists, inform the user that no such card exists
    - list existing cards if they **sort of match** the user selected card by [title], if any cards exist. You can find these cards by running [list_cards].
    - writes data: the card is removed and its [id] is not reused for another card
    - returns status "deleted" with the removed card's [id] and [title], or status "not_found" with a message; not found is a normal answer, not an error
    - an error result means neither [id] nor [title] was given; call again with one of them
    - examples: [id] "3"; [title] "Book flights"

    Args:
        id: The card's UID.
        title: The card's title. Case-insensitive, otherwise exact.

    Returns:
        A JSON string. Its shape is described in the bullets above, which are
        the only part of this docstring the model sees besides Args.

    Raises:
        ToolError: Neither id nor title was given. run_tool turns it into an
            is_error tool_result.
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
