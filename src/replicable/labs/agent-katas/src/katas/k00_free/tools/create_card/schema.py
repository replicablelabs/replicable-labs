from ...utils.utils import load_description

schema = {
    "name": "create_card",
    "description": load_description(__file__),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The card's name"},
            "content": {"type": "string", "description": "The card's content"},
            "replace": {
                "type": "boolean",
                "description": "Set to true only after the user agreed to replace the existing card with this title",
            },
        },
        "required": ["title", "content"],
        "additionalProperties": False,
    },
}
