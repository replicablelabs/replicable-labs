from ...utils.utils import load_description

schema = {
    "name": "delete_card",
    "description": load_description(__file__),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The card's name"},
            "id": {"type": "string", "description": "The card's UID"},
        },
        "required": [],
        "additionalProperties": False,
    },
}
