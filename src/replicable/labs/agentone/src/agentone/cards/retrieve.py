"""Hybrid retrieval: vector KNN (sqlite-vec) + graph k-hop (recursive CTE) around entities named in the query,
fused with reciprocal-rank fusion. `exclude` removes cards AND their edges (exercise mode must never retrieve the card being tested)."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from .embed import Embedder
from .models import Card
from .store import CardStore

@dataclass
class Retrieval:
    cards: list[Card] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)

def _graph_side(store: CardStore, query: str, hops: int, exclude) -> tuple[list[str], list[str]]:
    seeds = store.link_entities(query, exclude)
    if not seeds: return [], []
    weight: Counter = Counter(); facts = set()
    for r in store.neighborhood(seeds, hops, exclude):
        facts.add(f"{r['subject']} --{r['relation']}--> {r['object']}")
        weight[r["card_id"]] += 2 if (r["subject_key"] in seeds or r["object_key"] in seeds) else 1
    return [c for c, _ in sorted(weight.items(), key=lambda x: (-x[1], x[0]))], sorted(facts)

def retrieve(store: CardStore, embedder: Embedder, query: str, k: int = 3, hops: int = 1,
             mode: str = "hybrid", exclude=()) -> Retrieval:
    vec_ids = [c.id for c, _ in store.search(embedder.embed([query])[0], k * 2, exclude)] if mode in ("vector", "hybrid") else []
    graph_ids, facts = _graph_side(store, query, hops, exclude) if mode in ("graph", "hybrid") else ([], [])
    score: Counter = Counter()
    for ranking in (vec_ids, graph_ids):
        for r, cid in enumerate(ranking): score[cid] += 1 / (60 + r)   # reciprocal rank fusion
    top = [c for c, _ in sorted(score.items(), key=lambda x: (-x[1], x[0]))[:k]]
    return Retrieval([store.get(c) for c in top], facts)
