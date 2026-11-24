"""Cases for deleting cards. The fields are described in `create_card.py`, plus:

- `deleted`: titles of the seed cards removed, none if absent.
- `judge`: yes/no questions about the answer for an LLM, with the expected reply.
"""

from tools import delete_card, find_card, get_card, list_cards

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
            # system prompt doesn't specify an answer format, so we need a judge
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
        # Only one card matches, so the agent deletes it without asking.
        "inputs": {"prompt": "Delete my buy milk card."},
        "reference_outputs": {
            "created": [],
            "deleted": ["Buy milk"],
            "allowed_tools": [
                delete_card.name,
                find_card.name,
                get_card.name,
                list_cards.name,
            ],
            "forbidden_calls": [],
            # The deletion format in prompts/system.md; the first seed card has ID 1.
            "answer_contains": ["# Title: Buy milk", "# ID: 1", "removed"],
        },
        "metadata": {"name": "delete_existing"},
    },
]
