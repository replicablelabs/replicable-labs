from ... import db
from ...utils.utils import ToolError


def get_card(id=None, title=None):
    if not id and not title:
        raise ToolError("Provide the card's id or title.")
    card = db.find_card(id, title)
    if card is None:
        return {
            "status": "not_found",
            "message": "No card matches. If both id and title are given they must refer to the same card.",
        }
    return {"status": "found", "card": card.to_dict()}
