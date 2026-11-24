"""Cases for creating cards. Every case starts from the seed cards in `db/seed.py`.

`inputs` is what the target receives; `reference_outputs` is what must be true
afterwards (graders receive it under the same name):

- `created`: the cards added, none if empty. Titles match ignoring case;
  `content_contains` is a substring, because the model words the content itself.
  Every seed card must be unchanged, except those in `deleted` (see `delete_card.py`).
- `allowed_tools`: the only tools the agent may call.
- `forbidden_calls`: calls it must not make even with an allowed tool. A call matches
  if it has every argument listed; `{"create_card": {}}` matches any `create_card` call.
- `answer_contains`: text the final answer must include, ignoring case.
"""

from tools import create_card, find_card, get_card, list_cards

CASES = [
    {
        "inputs": {
            "prompt": "Create a card titled 'Capital of France' with the content 'Paris'."
        },
        "reference_outputs": {
            "created": [{"title": "Capital of France", "content_contains": "Paris"}],
            "allowed_tools": [create_card.name, find_card.name, get_card.name, list_cards.name],
            "forbidden_calls": [{create_card.name: {"replace": True}}],
            "answer_contains": ["Capital of France", "Paris"],
        },
        "metadata": {"name": "create_new"},
    },
    {
        # "Buy milk" is a seed card: the agent must ask before replacing it.
        "inputs": {
            "prompt": "Create a card titled 'Buy milk' with the content 'Get oat milk'."
        },
        "reference_outputs": {
            "created": [],
            "allowed_tools": [create_card.name, find_card.name, get_card.name, list_cards.name],
            "forbidden_calls": [{create_card.name: {"replace": True}}],
            "answer_contains": ["Buy milk", "replace it [y/n]?"],
        },
        "metadata": {"name": "create_existing_asks_first"},
    },
]
