from ...utils.utils import load_description

schema = {
    "name": "find_card",
    "description": load_description(__file__),
    "input_schema": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "The card's ID"},
            "title": {"type": "string", "description": "Words from the card's title"},
            "content": {"type": "string", "description": "Words from the card's content"},
        },
        "required": [],
        "additionalProperties": False,
    },
}
