from ... import db


def create_card(title, content, replace=False):
    existing = db.get_card_by_title(title)
    if existing is None:
        card = db.add_card(title, content)
        return {"status": "created", "card": card.to_dict()}
    if not replace:
        # Not an error: the model must ask the user, then call again with replace=true.
        return {"status": "exists", "card": existing.to_dict()}
    card = db.update_card(existing.id, content)
    return {"status": "replaced", "card": card.to_dict()}
