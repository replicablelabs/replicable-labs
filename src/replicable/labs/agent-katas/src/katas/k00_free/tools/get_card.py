from .. import db
from ..utils.utils import ToolError
from .base import tool
from .schemas import CardView, Result


@tool
def get_card(id: str = "", title: str = "") -> Result:
    """Get one card by its exact id or exact title.

    Returns the full card, including its content. Use it when you already know
    which card the user means; it does not search.

    - provide [id], [title] or both; if you provide both they must belong to the same card
    - title matching ignores letter case but must otherwise be an **exact match**
    - use [find_card] if you only know part of the title or something from the content
    - use [list_cards] to see every card, e.g. when you couldn't find a card with that [title] or [id]
    - read-only: it never changes a card
    - returns status "found" with the card ([id], [title], [content] and [scheduled_at] if the card is scheduled), or status "not_found" with a message; not found is a normal answer, not an error
    - an error result means neither [id] nor [title] was given; call again with one of them
    - examples: [id] "2"; [title] "Buy milk"; [id] "1" together with [title] "Buy milk" (only if they are the same card)

    Args:
        id: The card's UID, as returned by list_cards, find_card or create_card.
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
    card = db.find_card(id, title)
    if card is None:
        return Result.not_found()
    return Result(status="found", card=CardView.full(card))
