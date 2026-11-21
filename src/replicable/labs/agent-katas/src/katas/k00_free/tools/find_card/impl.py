from ... import db
from ...utils.utils import ToolError


def find_card(id=None, title=None, content=None):
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
    return {"matches": matches}
