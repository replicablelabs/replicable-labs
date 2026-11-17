"""Offline evals for the cards app. retrieval_eval needs no LLM/key. router_eval & judge_eval take an LLM."""
from __future__ import annotations
import tempfile
from pathlib import Path
from .embed import Embedder
from .models import RouteDecision, Score
from .retrieve import retrieve
from .seed import load_seed, retrieval_queries
from .store import CardStore

def retrieval_eval(embedder: Embedder, k: int = 3) -> dict[str, float]:
    """recall@k of the expected card, for vector-only / graph-only / hybrid, on the seed deck."""
    with tempfile.TemporaryDirectory() as d:
        store = CardStore(Path(d) / "eval.db", embedder.name, embedder.dim); load_seed(store, embedder); qs = retrieval_queries()
        return _recall(store, embedder, qs, k)

def _recall(store, embedder, qs, k):
    return {m: round(sum(q["card"] in [c.id for c in retrieve(store, embedder, q["query"], k=k, mode=m).cards] for q in qs) / len(qs), 2)
            for m in ("vector", "graph", "hybrid")}

ROUTER_CASES = [  # (mode, message, expected intent)
    ("study", "why does the tool result need a matching id?", "ask"),
    ("study", "can you make a card about checkpointers?", "create_card"),
    ("study", "turn that into a flashcard please", "create_card"),
    ("exercise", "give me a hint", "ask"),
    ("exercise", "I think it's a single user message with matching tool_use_ids", "submit_answer"),
    ("exercise", "my final answer: it saves state per thread_id", "submit_answer"),
]
def router_eval(llm) -> float:
    from .session import ROUTE_SYSTEM
    return sum(llm.structured(ROUTE_SYSTEM[m], t, RouteDecision).intent == want for m, t, want in ROUTER_CASES) / len(ROUTER_CASES)

JUDGE_CASES = [  # (question, expected, learner answer, expected verdict)
    ("Where do tool_result blocks go?", "In a single user message with matching tool_use_ids.", "One user message, each with the right tool_use_id", "correct"),
    ("Where do tool_result blocks go?", "In a single user message with matching tool_use_ids.", "In the assistant message", "incorrect"),
    ("Why GraphRAG?", "Explicit edges let retrieval follow entity chains for multi-hop questions.", "It uses a graph", "partial"),
]
def judge_eval(llm) -> float:
    from .session import JUDGE_SYSTEM
    ok = sum(llm.structured(JUDGE_SYSTEM, f"Question: {q}\nExpected answer: {e}\nLearner's answer: {a}", Score).verdict == v
             for q, e, a, v in JUDGE_CASES)
    return ok / len(JUDGE_CASES)
