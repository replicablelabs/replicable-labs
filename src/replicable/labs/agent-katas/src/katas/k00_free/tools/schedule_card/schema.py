from ...utils.utils import load_description

schema = {
    "name": "schedule_card",
    "description": load_description(__file__),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The card's name"},
            "id": {"type": "string", "description": "The card's UID"},
            "scheduled_at": {
                "type": "string",
                "description": "When to study the card, ISO 8601, e.g. 2026-11-25T09:00",
            },
        },
        "required": ["scheduled_at"],
        "additionalProperties": False,
    },
}
