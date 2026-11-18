"""Vector store + semantic search: Qdrant. One point per card; payload carries the card content (question/answer)."""
from __future__ import annotations
import uuid
from qdrant_client import QdrantClient, models
from .models import Card

_NS = uuid.UUID("6f1c3b7e-0a55-4d0e-9d3e-5a6b7c8d9e01")   # Qdrant ids must be uuid/int: derive deterministically from card id
def _pid(card_id: str) -> str: return str(uuid.uuid5(_NS, card_id))

class QdrantIndex:
    def __init__(self, url: str | None = None, dim: int = 0, collection: str = "cards", client: QdrantClient | None = None):
        self.c = client or QdrantClient(url=url)
        self.collection = collection
        if self.c.collection_exists(collection):
            size = self.c.get_collection(collection).config.params.vectors.size
            if size != dim: raise ValueError(f"Qdrant collection '{collection}' has vector size {size}, embedder gives {dim}. "
                                             "Use the same EMBEDDING_* or drop the collection.")
        else:
            self.c.create_collection(collection, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))
            self.c.create_payload_index(collection, "card_id", models.PayloadSchemaType.KEYWORD)

    def close(self) -> None: self.c.close()

    def upsert(self, card: Card, vector: list[float]) -> None:
        self.c.upsert(self.collection, points=[models.PointStruct(
            id=_pid(card.id), vector=vector, payload={"card_id": card.id, "question": card.question, "answer": card.answer})])

    def delete(self, card_id: str) -> None:
        self.c.delete(self.collection, points_selector=models.PointIdsList(points=[_pid(card_id)]))

    def search(self, vec: list[float], k: int, exclude=()) -> list[tuple[str, float]]:
        flt = models.Filter(must_not=[models.FieldCondition(key="card_id", match=models.MatchAny(any=list(exclude)))]) if exclude else None
        r = self.c.query_points(self.collection, query=vec, limit=k, query_filter=flt, with_payload=True)
        return [(p.payload["card_id"], p.score) for p in r.points]

    def vector_of(self, card_id: str) -> list[float] | None:
        r = self.c.retrieve(self.collection, ids=[_pid(card_id)], with_vectors=True)
        return list(r[0].vector) if r else None
