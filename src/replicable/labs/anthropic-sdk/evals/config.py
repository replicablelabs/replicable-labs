"""Environment for eval runs. Call `configure()` before running the agent."""

import os
from pathlib import Path

from dotenv import load_dotenv

LAB = Path(__file__).resolve().parent.parent
DEFAULT_PROJECT = "anthropic-sdk-evals"


def configure() -> str:
    """Load the lab's .env and send traces to the evals project; returns its name.

    A LangSmith experiment gets its own project, so this one only receives agent
    runs made outside an experiment.

    Must run before the first trace: LangSmith caches the project name.
    """
    load_dotenv(LAB / ".env", override=False)
    project = os.environ.get("LANGSMITH_EVALS_PROJECT") or DEFAULT_PROJECT
    os.environ["LANGSMITH_PROJECT"] = project
    return project
