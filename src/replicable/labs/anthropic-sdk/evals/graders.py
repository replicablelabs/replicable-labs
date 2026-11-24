"""Functions that judge one run. Each returns True if the run passes.

`outputs` is what the target returned: {"answer": str, "tool_calls": list, "cards": list}.
`reference_outputs` is the case's expected result (see `cases/`).
"""


def desired_answer(outputs: dict, reference_outputs: dict) -> bool:
    """The answer includes every `answer_contains` string, ignoring case."""
    raise NotImplementedError


def only_allowed_tools(outputs: dict, reference_outputs: dict) -> bool:
    """Every call is to an `allowed_tools` tool and matches none of `forbidden_calls`."""
    raise NotImplementedError


def desired_result(outputs: dict, reference_outputs: dict) -> bool:
    """Seed cards are unchanged and the only new cards are those in `created`."""
    raise NotImplementedError


def desired_answer_judged(outputs: dict, reference_outputs: dict) -> bool:
    """An LLM's reply to every `judge` question is the expected one (cases without `judge`: undecided)."""
    raise NotImplementedError
