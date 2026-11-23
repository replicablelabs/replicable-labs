import db
from utils.utils import ToolError
from .base import tool
from .schemas import Card, Result, Status


@tool
def delete_card(id: str = "", title: str = "") -> Result:
    """Delete a card permanently.

    There is no undo. Be sure which card the user means before calling it.

    - delete a card by [id] or by [title]; provide at least one, and if you provide both they must belong to the same card
    - get the card with [get_card] for exact matches, otherwise follow the instructions at [get_card] to get the card
    - if the user described the card loosely, use [find_card] or [list_cards] to identify it first, and confirm with the user when more than one card could match
    - if no such card exists, inform the user that no such card exists
    - list existing cards if they **sort of match** the user selected card by [title], if any cards exist. You can find these cards by running [list_cards].
    - writes data: the card is removed and its [id] is not reused for another card
    - returns [status] "deleted" with [cards] holding the removed card's [id] and [title], or [status] "not_found" with a [message] and an empty [cards]; not found is a normal answer, not an error
    - an error result means neither [id] nor [title] was given; call again with one of them
    - examples: [id] "3"; [title] "Book flights"

    Args:
        id: The card's UID.
        title: The card's title. Case-insensitive, otherwise exact.

    Returns:
        A `Result` (see schemas.py), which @tool serialises to the JSON string
        the model reads. Its shape is described in the bullets above, the only
        part of this docstring besides Args that the model sees.

    Raises:
        ToolError: Neither id nor title was given. run_tool turns it into an
            is_error tool_result.
    """
    if not id and not title:
        raise ToolError("Provide the card's id or title.")
    card = db.delete_card(id, title)
    if card is None:
        return Result.not_found()
    return Result(status=Status.DELETED, cards=[Card.brief(card)])
