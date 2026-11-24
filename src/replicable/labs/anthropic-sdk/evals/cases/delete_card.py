"""Cases for deleting cards. The fields are described in `create_card.py`, plus:

- `judge`: yes/no questions about the answer for an LLM, with the expected reply.
"""

from tools import (
    create_card,
    delete_card,
    find_card,
    get_card,
    list_cards,
    schedule_card,
)

CASES = [
    {
        # No such seed card. Calling `delete_card` is allowed: it returns "not_found".
        "inputs": {"prompt": "Delete my dentist card."},
        "reference_outputs": {
            "created": [],
            "allowed_tools": [
                delete_card.name,
                find_card.name,
                get_card.name,
                list_cards.name,
            ],
            "forbidden_calls": [],
            "answer_contains": ["dentist"],
            "judge": [
                {
                    "question": "Does the reply say that no dentist card exists?",
                    "expected": True,
                },
                {
                    "question": "Does the reply claim that a card was deleted?",
                    "expected": False,
                },
            ],
        },
        "metadata": {"name": "delete_missing"},
    },
    {
        # "Buy milk" is a seed card: the agent must ask before deleting it.
        "inputs": {"prompt": "Delete my buy milk card."},
        "reference_outputs": {
            "created": [],
            "allowed_tools": [
                delete_card.name,
                find_card.name,
                get_card.name,
                list_cards.name,
            ],
            "forbidden_calls": [],
            "answer_contains": ["milk"],
            "judge": [
                {
                    "question": "Does the reply say that the milk card has been deleted?",
                    "expected": True,
                }
            ],
        },
        "metadata": {"name": "delete_existing"},
    },
]
