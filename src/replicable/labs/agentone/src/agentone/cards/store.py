"""Card store: cards + vectors (embedding) + triples (graph) + attempts. One JSON file; the graph is derived."""
from __future__ import annotations
from pathlib import Path
import networkx as nx
from pydantic import BaseModel, Field
from .embed import cosine
from .models import Attempt, Card, Triple

class StoreState(BaseModel):
    cards: dict[str, Card] = Field(default_factory=dict)
    vectors: dict[str, list[float]] = Field(default_factory=dict)   # the VECTOR side
    triples: dict[str, list[Triple]] = Field(default_factory=dict)  # the GRAPH side (edge provenance = card id)
    attempts: list[Attempt] = Field(default_factory=list)

class CardStore:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.s = StoreState.model_validate_json(path.read_text()) if path and path.exists() else StoreState()

    def save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(self.s.model_dump_json(indent=1))

    def add(self, card: Card, vector: list[float], triples: list[Triple]) -> None:
        self.s.cards[card.id] = card; self.s.vectors[card.id] = vector; self.s.triples[card.id] = triples; self.save()

    def get(self, card_id: str) -> Card: return self.s.cards[card_id]

    def search(self, vec: list[float], k: int, exclude=()) -> list[tuple[Card, float]]:
        scored = [(self.s.cards[i], cosine(vec, v)) for i, v in self.s.vectors.items() if i not in exclude]
        return sorted(scored, key=lambda x: (-x[1], x[0].id))[:k]

    def graph(self, exclude=()) -> nx.MultiDiGraph:
        """Entities = nodes (case-insensitive key, original label). Edges = triples, each tagged with its card_id."""
        g = nx.MultiDiGraph()
        for cid, ts in self.s.triples.items():
            if cid in exclude: continue
            for t in ts:
                for name in (t.subject, t.object):
                    if name.lower() not in g: g.add_node(name.lower(), label=name)
                g.add_edge(t.subject.lower(), t.object.lower(), relation=t.relation, card_id=cid)
        return g

    def record(self, a: Attempt) -> None: self.s.attempts.append(a); self.save()

    def mean_score(self, card_id: str) -> float | None:
        xs = [a.score for a in self.s.attempts if a.card_id == card_id]
        return sum(xs) / len(xs) if xs else None

    def next_card(self, mode: str, exclude=()) -> Card | None:
        cards = [c for c in self.s.cards.values() if c.id not in exclude]
        if not cards: return None
        if mode == "study": return min(cards, key=lambda c: c.created_at)
        # exercise: never-attempted first, then weakest
        return min(cards, key=lambda c: (self.mean_score(c.id) if self.mean_score(c.id) is not None else -1.0, c.created_at))
