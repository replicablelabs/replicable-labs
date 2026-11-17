"""ONLINE evals: score real/live traffic, no reference answer. Tracing + reference-free evaluators + feedback.

LangSmith flow: @traceable every request -> project collects runs -> an *online evaluator rule* (UI) samples
runs (e.g. 10%), applies an LLM-judge/code evaluator, writes feedback. Programmatic equivalent below."""
from __future__ import annotations
import random
from langsmith import Client, traceable
from agentone.loop import run_agent

@traceable(name="agentone", run_type="chain")
def handle(question: str) -> str:
    return run_agent(question).answer

# reference-free checks (no ground truth in production):
def no_giving_up(answer: str) -> float: return float("max_steps" not in answer)
def grounded(answer: str, facts: str) -> float:  # cheap groundedness: answer tokens appear in retrieved facts
    toks = [t for t in answer.lower().split() if len(t) > 3]
    return sum(t in facts.lower() for t in toks) / max(len(toks), 1)

def sample_and_score(project="agentone", rate=0.1, limit=50):
    c = Client()
    for run in c.list_runs(project_name=project, is_root=True, limit=limit):
        if random.random() > rate or not run.outputs: continue
        c.create_feedback(run.id, key="no_giving_up", score=no_giving_up(str(run.outputs)))

def user_feedback(run_id, thumbs_up: bool):  # the other online signal: explicit user feedback
    Client().create_feedback(run_id, key="user_score", score=float(thumbs_up))
