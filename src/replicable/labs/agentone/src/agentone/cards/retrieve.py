"""Hybrid retrieval: vector top-k  +  graph neighbourhood of entities named in the query, fused with RRF.
`exclude` removes cards AND their edges (exercise mode must never retrieve the card being tested)."""
from __future__ import annotations
import re
from collections import Counter
from dataclasses import dataclass, field
import networkx as nx
from .embed import Embedder
from .models import Card
from .store import CardStore

@dataclass
class Retrieval:
    cards: list[Card] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)

def _graph_side(store: CardStore, query: str, hops: int, exclude) -> tuple[list[str], list[str]]:
    g = store.graph(exclude)
    q = query.lower()
    seeds = [n for n in g.nodes if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", q)]  # entity linking
    if not seeds: return [], []
    und = g.to_undirected(as_view=True)
    reach: set[str] = set()
    for s in seeds: reach |= set(nx.single_source_shortest_path_length(und, s, cutoff=hops))
    weight: Counter = Counter(); facts = set()
    for u, v, d in g.edges(data=True):
        if u in reach and v in reach:
            facts.add(f"{g.nodes[u]['label']} --{d['relation']}--> {g.nodes[v]['label']}")
            weight[d["card_id"]] += 2 if (u in seeds or v in seeds) else 1
    ranked = [c for c, _ in sorted(weight.items(), key=lambda x: (-x[1], x[0]))]
    return ranked, sorted(facts)

def retrieve(store: CardStore, embedder: Embedder, query: str, k: int = 3, hops: int = 1,
             mode: str = "hybrid", exclude=()) -> Retrieval:
    vec_ids = [c.id for c, _ in store.search(embedder.embed([query])[0], k * 2, exclude)] if mode in ("vector", "hybrid") else []
    graph_ids, facts = _graph_side(store, query, hops, exclude) if mode in ("graph", "hybrid") else ([], [])
    score: Counter = Counter()
    for ranking in (vec_ids, graph_ids):
        for r, cid in enumerate(ranking): score[cid] += 1 / (60 + r)   # reciprocal rank fusion
    top = [c for c, _ in sorted(score.items(), key=lambda x: (-x[1], x[0]))[:k]]
    return Retrieval([store.get(c) for c in top], facts)
