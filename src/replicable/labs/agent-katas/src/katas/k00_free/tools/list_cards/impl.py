import json

from anthropic import beta_tool

from ... import db


@beta_tool
def list_cards() -> str:
    """List all the existing cards.

    - List all the existing cards, showing their [id] and [title]
    """
    return json.dumps({"cards": [{"id": c.id, "title": c.title} for c in db.list_cards()]})
