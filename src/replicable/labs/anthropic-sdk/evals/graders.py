"""Functions that judge one run. Each returns True if the run passes.

`outputs` is what the target returned: {"answer": str, "tool_calls": list, "cards": list,
"stop_reason": str}; empty or None if the run crashed, which fails.
`reference_outputs` is the case's expected result (see `cases/`).
"""

from db.seed import SAMPLES
from evals import judge


def desired_answer(outputs: dict, reference_outputs: dict) -> bool:
    """The answer includes every `answer_contains` string, ignoring case."""
    answer = (outputs or {}).get("answer")
    if not answer:
        return False  # a crashed or unfinished run
    answer = answer.casefold()
    return all(
        text.casefold() in answer for text in reference_outputs["answer_contains"]
    )


def only_allowed_tools(outputs: dict, reference_outputs: dict) -> bool:
    """Every call is to an `allowed_tools` tool and matches none of `forbidden_calls`."""
    tool_calls = (outputs or {}).get("tool_calls")
    if tool_calls is None:
        return False  # a crashed run; an empty list is fine: no calls were made
    for call in tool_calls:
        for name, arguments in call.items():
            if name not in reference_outputs["allowed_tools"]:
                return False
            for forbidden in reference_outputs["forbidden_calls"]:
                if name in forbidden and _includes(arguments, forbidden[name]):
                    return False
    return True


def _includes(arguments: dict, conditions: dict) -> bool:
    """True if `arguments` has every condition's value; always true for `{}`."""
    return all(
        key in arguments and arguments[key] == value
        for key, value in conditions.items()
    )


def desired_result(outputs: dict, reference_outputs: dict) -> bool:
    """The final cards are the unchanged seed cards, minus `deleted`, plus `created`."""
    cards = (outputs or {}).get("cards")
    if cards is None:
        return False  # a crashed run
    seeds = [
        {"id": str(id), "title": title, "content": content}
        for id, (title, content) in enumerate(SAMPLES, start=1)
    ]
    seed_ids = {seed["id"] for seed in seeds}
    deleted = reference_outputs.get("deleted", [])
    unknown = set(deleted) - {seed["title"] for seed in seeds}
    if unknown:
        raise ValueError(f"`deleted` names no seed card: {unknown}")

    kept = [card for card in cards if card["id"] in seed_ids]
    new = [card for card in cards if card["id"] not in seed_ids]
    created = reference_outputs["created"]
    return (
        kept == [seed for seed in seeds if seed["title"] not in deleted]
        and len(new) == len(created)
        # Titles are unique, so equal counts and a match for each is one-to-one.
        and all(any(_matches(card, expected) for card in new) for expected in created)
    )


def _matches(card: dict, expected: dict) -> bool:
    """True if an unscheduled `card` has the expected title and content, ignoring case."""
    return (
        card["title"].casefold() == expected["title"].casefold()
        and expected["content_contains"].casefold() in card["content"].casefold()
        and "scheduled_at" not in card
    )


def desired_answer_judged(outputs: dict, reference_outputs: dict) -> bool | dict:
    """An LLM gives the expected reply to every `judge` question.

    A case without `judge` gets no score (an empty result list), not a free pass.
    """
    questions = reference_outputs.get("judge")
    if not questions:
        return {"results": []}
    answer = (outputs or {}).get("answer")
    if not answer:
        return False  # a crashed or unfinished run
    return all(judge.ask(q["question"], answer) is q["expected"] for q in questions)
