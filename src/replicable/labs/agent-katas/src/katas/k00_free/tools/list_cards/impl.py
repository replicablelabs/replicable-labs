from ... import db


def list_cards():
    return {"cards": [{"id": c.id, "title": c.title} for c in db.list_cards()]}
