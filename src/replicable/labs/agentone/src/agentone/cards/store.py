"""CardStore = facade over three real stores, each owning what it is best at:

  PostgresCards  (pg.py)       relational: cards, attempts, meta        -- source of truth for identity
  QdrantIndex    (vectors.py)  vectors + semantic search over card content
  Neo4jGraph     (graph.py)    knowledge graph of entities/relations extracted from cards

There is no cross-database transaction. `add` writes Postgres -> Qdrant -> Neo4j and, if a later step fails, undoes the
earlier ones (compensation). Interview talking point: dual-write problem; production answers = outbox pattern / idempotent
re-index jobs keyed by card id.
"""
from __future__ import annotations
from .models import Attempt, Card, Triple

class CardStore:
    def __init__(self, cards, vectors, graph, embedder_name: str):
        self.pg, self.vec, self.graph = cards, vectors, graph
        pinned = self.pg.get_meta("embedder")
        if pinned is None: self.pg.set_meta("embedder", embedder_name)
        elif pinned != embedder_name:
            raise ValueError(f"This database was indexed with embedder '{pinned}', but EMBEDDING_* now selects '{embedder_name}'. "
                             "Switch back, or re-index into fresh databases.")

    def close(self) -> None:
        for b in (self.pg, self.vec, self.graph): b.close()

    # ---- write ----
    def add(self, card: Card, vector: list[float], triples: list[Triple]) -> None:
        self.pg.add(card)
        try:
            self.vec.upsert(card, vector)
            try: self.graph.add_triples(card.id, triples)
            except Exception: self.vec.delete(card.id); raise
        except Exception:
            self.pg.delete(card.id); raise

    def record(self, a: Attempt) -> None: self.pg.record(a)

    # ---- relational ----
    def has(self, card_id): return self.pg.has(card_id)
    def get(self, card_id): return self.pg.get(card_id)
    def cards(self): return self.pg.all()
    def count(self): return self.pg.count()
    def attempts(self, card_id=None): return self.pg.attempts(card_id)
    def mean_score(self, card_id): return self.pg.mean_score(card_id)
    def next_card(self, mode, exclude=()): return self.pg.next_card(mode, exclude)

    # ---- vectors ----
    def vector_of(self, card_id): return self.vec.vector_of(card_id)
    def search(self, vec, k, exclude=()) -> list[tuple[Card, float]]:
        return [(self.pg.get(cid), s) for cid, s in self.vec.search(vec, k, exclude)]

    # ---- graph ----
    def link_entities(self, query, exclude=()): return self.graph.link_entities(query, exclude)
    def neighborhood(self, seeds, hops, exclude=()): return self.graph.neighborhood(seeds, hops, exclude)
    def triples_of(self, card_id): return self.graph.triples_of(card_id)
    def stats(self): return self.graph.stats()
    def edges(self): return self.graph.edges()
