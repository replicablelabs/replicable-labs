"""The eval runner, with a scripted agent and a fake LangSmith (no API key needed)."""

from types import SimpleNamespace

import agent
import db
import pytest

from evals import run


def finished(result="Done"):
    """A finished agent state."""
    state = agent.AgentState.start("hi")
    state.result, state.stop_reason = result, "end_turn"
    return state


def test_target_starts_from_the_seed_cards_and_reports_the_run(monkeypatch):
    """Leftovers of an earlier case are gone; the changes of this one are reported."""

    def fake_agent(client, prompt):
        """Delete card 1, as the model would through a tool."""
        assert len(db.list_cards()) == 3 and prompt == "p"
        db.delete_card(id="1")
        return finished()

    monkeypatch.setattr(agent, "run", fake_agent)
    db.add_card("leftover", "from another case")

    outputs = run.make_target(client=None)({"prompt": "p"})
    db.reset()  # the next case must not change what was reported

    assert [card["id"] for card in outputs["cards"]] == ["2", "3"]
    assert (outputs["answer"], outputs["tool_calls"], outputs["stop_reason"]) == ("Done", [], "end_turn")


class FakeLangSmith:
    """Just enough of `langsmith.Client` to hold one dataset."""

    def __init__(self):
        self.examples = None
        self.writes = []

    def has_dataset(self, dataset_name):
        return self.examples is not None

    def create_dataset(self, name):
        self.examples = []

    def list_examples(self, dataset_name):
        return iter(list(self.examples))

    def create_example(self, dataset_name, inputs, reference_outputs, metadata):
        self.writes.append("create")
        self.examples.append(
            SimpleNamespace(id=len(self.examples), inputs=inputs, outputs=reference_outputs, metadata=metadata)
        )

    def update_example(self, example_id, inputs, outputs):
        self.writes.append("update")
        self.examples[example_id].inputs, self.examples[example_id].outputs = inputs, outputs


@pytest.fixture
def langsmith():
    """A fake LangSmith that already holds the cases."""
    fake = FakeLangSmith()
    run.sync_dataset(fake)
    return fake


def test_first_sync_uploads_every_case(langsmith):
    """The dataset is created with one example per case."""
    assert langsmith.writes == ["create"] * len(run.CASES)


def test_second_sync_changes_nothing(langsmith):
    """Unchanged cases are not uploaded again."""
    langsmith.writes.clear()
    assert len(run.sync_dataset(langsmith)) == len(run.CASES)
    assert langsmith.writes == []


def test_edited_case_is_updated(langsmith):
    """A case that differs from its example replaces it."""
    langsmith.writes.clear()
    langsmith.examples[0].inputs = {"prompt": "old"}
    run.sync_dataset(langsmith)
    assert langsmith.writes == ["update"]
    assert langsmith.examples[0].inputs == run.CASES[0]["inputs"]


def test_removed_case_is_not_run(langsmith, monkeypatch):
    """An example without a case stays in LangSmith but is left out of the experiment."""
    monkeypatch.setattr(run, "CASES", run.CASES[1:])
    assert len(run.sync_dataset(langsmith)) == len(run.CASES)


def test_case_names_are_unique():
    """Examples are matched by name, so two cases cannot share one."""
    names = [case["metadata"]["name"] for case in run.CASES]
    assert len(names) == len(set(names))
