"""The eval graders, on hand-made runs (no API key needed)."""

import pytest
from types import SimpleNamespace

import db
from evals import judge
from evals.graders import (
    desired_answer,
    desired_answer_judged,
    desired_result,
    only_allowed_tools,
)

EXISTS = "# Title: Buy milk\nThe card already exists, replace it [y/n]?"


@pytest.mark.parametrize(
    "outputs, passes",
    [
        ({"answer": EXISTS}, True),
        ({"answer": EXISTS.upper()}, True),
        ({"answer": "# Title: Buy milk\nCreated."}, False),
        ({"answer": ""}, False),
        ({}, False),
        (None, False),
    ],
    ids=["correct", "other case", "one string missing", "empty", "no answer", "crashed"],
)
def test_desired_answer(outputs, passes):
    """Every expected string must be there; a run without an answer fails."""
    reference = {"answer_contains": ["Buy milk", "replace it [y/n]?"]}
    assert desired_answer(outputs, reference) is passes


@pytest.mark.parametrize("outputs, passes", [({"answer": "Hi"}, True), ({"answer": ""}, False)])
def test_desired_answer_without_expected_text_still_needs_an_answer(outputs, passes):
    """An empty `answer_contains` accepts any answer, but not a missing one."""
    assert desired_answer(outputs, {"answer_contains": []}) is passes


GOOD = {"create_card": {"title": "A", "content": "B"}}
REPLACE = {"create_card": {"title": "A", "content": "B", "replace": True}}
SCHEDULE = {"schedule_card": {"id": "1", "scheduled_at": "2026-12-01"}}
TOOLS = {"allowed_tools": ["create_card"], "forbidden_calls": [{"create_card": {"replace": True}}]}


@pytest.mark.parametrize(
    "outputs, passes",
    [
        ({"tool_calls": []}, True),
        ({"tool_calls": [GOOD]}, True),
        ({"tool_calls": [{"create_card": {"title": "A", "replace": False}}]}, True),
        ({"tool_calls": [REPLACE]}, False),
        ({"tool_calls": [SCHEDULE]}, False),
        ({"tool_calls": [GOOD, REPLACE]}, False),
        ({}, False),
        (None, False),
    ],
)
def test_only_allowed_tools(outputs, passes):
    """Tools are checked by name, then by argument; no calls is fine, no evidence is not."""
    assert only_allowed_tools(outputs, TOOLS) is passes


@pytest.mark.parametrize(
    "forbidden, passes",
    [
        ({}, False),  # any call
        ({"title": "A", "replace": True}, False),  # both match
        ({"title": "Z", "replace": True}, True),  # only one matches
    ],
)
def test_forbidden_call_needs_every_listed_argument(forbidden, passes):
    """`{}` lists no conditions, so it forbids every call to the tool."""
    reference = {"allowed_tools": ["create_card"], "forbidden_calls": [{"create_card": forbidden}]}
    assert only_allowed_tools({"tool_calls": [REPLACE]}, reference) is passes


def cards_after(*changes):
    """The seed cards after `changes`, as the target reports them."""
    db.reset()
    for change in changes:
        change()
    return {"cards": [card.to_dict() for card in db.list_cards()]}


def add(title="Capital of France", content="Paris."):
    """A change that adds a card."""
    return lambda: db.add_card(title, content)


def delete(id):
    """A change that deletes a card."""
    return lambda: db.delete_card(id=id)


def schedule(id):
    """A change that schedules a card."""
    return lambda: db.set_schedule(id, "2026-12-01")


PARIS = {"created": [{"title": "capital of france", "content_contains": "paris"}]}
MILK_GONE = {"created": [], "deleted": ["Buy milk"]}
UNCHANGED = {"created": []}


@pytest.mark.parametrize(
    "changes, reference, passes",
    [
        ([], UNCHANGED, True),
        ([add()], UNCHANGED, False),
        ([delete("1")], UNCHANGED, False),
        ([schedule("1")], UNCHANGED, False),
        ([lambda: db.update_card("1", "new")], UNCHANGED, False),
        ([delete("1"), lambda: db.add_card(*db.seed.SAMPLES[0])], UNCHANGED, False),
        ([add()], PARIS, True),
        ([], PARIS, False),
        ([add(content="Lyon")], PARIS, False),
        ([add(title="Other")], PARIS, False),
        ([add(), add("Extra")], PARIS, False),
        ([add(), schedule("4")], PARIS, False),
        ([add(), delete("3")], PARIS, False),
        ([delete("1")], MILK_GONE, True),
        ([], MILK_GONE, False),
        ([delete("2")], MILK_GONE, False),
        ([delete("1"), delete("2")], MILK_GONE, False),
    ],
)
def test_desired_result(changes, reference, passes):
    """The expected change happened and nothing else did."""
    assert desired_result(cards_after(*changes), reference) is passes


@pytest.mark.parametrize("outputs", [{}, None])
def test_desired_result_fails_a_crashed_run(outputs):
    """No cards is no evidence, even when nothing should change."""
    assert desired_result(outputs, UNCHANGED) is False


def test_desired_result_rejects_a_case_that_deletes_an_unknown_card():
    """A typo in a case is an error, not a fail."""
    with pytest.raises(ValueError, match="Buy mlik"):
        desired_result(cards_after(), {"created": [], "deleted": ["Buy mlik"]})


JUDGE = {"judge": [{"question": "missing?", "expected": True}, {"question": "deleted?", "expected": False}]}


@pytest.mark.parametrize(
    "verdicts, passes",
    [((True, False), True), ((False, False), False), ((True, True), False)],
)
def test_judged_answer_needs_every_expected_verdict(monkeypatch, verdicts, passes):
    """Each question catches a different mistake."""
    said = dict(zip(["missing?", "deleted?"], verdicts))
    monkeypatch.setattr(judge, "ask", lambda question, reply: said[question])
    assert desired_answer_judged({"answer": "Hi"}, JUDGE) is passes


def test_judge_is_not_called_without_a_question_or_an_answer(monkeypatch):
    """No questions: no score. No answer: a fail. Neither costs a model call."""
    monkeypatch.setattr(judge, "ask", lambda *args: pytest.fail("called"))
    assert desired_answer_judged({"answer": "Hi"}, {}) == {"results": []}
    assert desired_answer_judged({"answer": ""}, JUDGE) is False
    assert desired_answer_judged(None, JUDGE) is False


@pytest.mark.parametrize("stop_reason, verdict", [("refusal", None), ("max_tokens", None)])
def test_judge_without_a_verdict_is_an_error(monkeypatch, stop_reason, verdict):
    """A failed judge must not look like a wrong answer."""
    resp = SimpleNamespace(stop_reason=stop_reason, parsed_output=verdict)
    client = SimpleNamespace(messages=SimpleNamespace(parse=lambda **request: resp))
    monkeypatch.setattr(judge, "_client", lambda: client)
    with pytest.raises(RuntimeError, match=stop_reason):
        judge.ask("q", "reply")
