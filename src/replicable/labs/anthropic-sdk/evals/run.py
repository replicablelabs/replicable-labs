"""Run the cases against the real model as a LangSmith experiment.

uv run python -m evals.run                  # each case once
uv run python -m evals.run --repetitions 5  # each case five times
"""

import argparse

import agent
import db
from anthropic import Anthropic
from langsmith import Client

from evals.cases import create_card, delete_card
from evals.config import configure
from evals.graders import (
    desired_answer,
    desired_answer_judged,
    desired_result,
    only_allowed_tools,
)

DATASET = "anthropic-sdk"
CASES = create_card.CASES + delete_card.CASES
GRADERS = [desired_answer, only_allowed_tools, desired_result, desired_answer_judged]


def make_target(client: Anthropic):
    """Return the function LangSmith calls once per case."""

    def target(inputs: dict) -> dict:
        """Run the agent from the seed cards; return what the graders need."""
        db.reset()
        state = agent.run(client, inputs["prompt"])
        return {
            "answer": state.result,
            "tool_calls": state.metadata["tool_calls"],
            # Copied here: the next case resets the store.
            "cards": [card.to_dict() for card in db.list_cards()],
            "stop_reason": state.stop_reason,
        }

    return target


def sync_dataset(langsmith: Client) -> list:
    """Make the LangSmith dataset match `CASES`, by case name; return their examples.

    Examples whose case was removed here are left in the dataset but not returned.
    """
    if not langsmith.has_dataset(dataset_name=DATASET):
        langsmith.create_dataset(DATASET)
    existing = {
        (example.metadata or {}).get("name"): example
        for example in langsmith.list_examples(dataset_name=DATASET)
    }
    for case in CASES:
        example = existing.get(case["metadata"]["name"])
        if example is None:
            langsmith.create_example(dataset_name=DATASET, **case)
        elif (example.inputs, example.outputs) != (
            case["inputs"],
            case["reference_outputs"],
        ):
            langsmith.update_example(
                example.id, inputs=case["inputs"], outputs=case["reference_outputs"]
            )

    names = {case["metadata"]["name"] for case in CASES}
    return [
        example
        for example in langsmith.list_examples(dataset_name=DATASET)
        if (example.metadata or {}).get("name") in names
    ]


def main(argv=None) -> None:
    """Sync the dataset and run the experiment."""
    parser = argparse.ArgumentParser(description="Run the card-agent evals.")
    parser.add_argument("--repetitions", type=int, default=1, help="runs per case")
    args = parser.parse_args(argv)

    configure()  # before any client or trace: loads the keys and the project name
    langsmith = Client()
    langsmith.evaluate(
        make_target(Anthropic()),  # function that executes the agent against case input
        data=sync_dataset(langsmith),  # case input, expected output, rubrics ds
        evaluators=GRADERS,
        experiment_prefix="agent",
        metadata={"model": agent.MODEL},
        num_repetitions=args.repetitions,
        max_concurrency=0,  # the cases share one in-memory store
    )


if __name__ == "__main__":
    main()
