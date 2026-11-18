"""Real qdrant-client API against an on-disk local Qdrant (no server needed). Server-level checks live in test_integration.py."""
import pytest
from qdrant_client import QdrantClient
from agentone.cards.embed import HashEmbedder
from agentone.cards.models import Card
from agentone.cards.vectors import QdrantIndex

E = HashEmbedder()

def test_upsert_search_exclude_retrieve_delete(tmp_path):
    q = QdrantIndex(dim=E.dim, client=QdrantClient(path=str(tmp_path / "q")))
    cards = [Card(id="a", question="checkpointer saves state", answer="x"), Card(id="b", question="vector cosine", answer="y")]
    for c in cards: q.upsert(c, E.embed([c.question])[0])
    qv = E.embed(["checkpointer state"])[0]
    assert q.search(qv, 2)[0][0] == "a" and q.search(qv, 2, exclude=["a"])[0][0] == "b"
    assert len(q.vector_of("a")) == E.dim
    q.delete("a"); assert q.vector_of("a") is None

def test_dim_mismatch_refused(tmp_path):
    c = QdrantClient(path=str(tmp_path / "q")); QdrantIndex(dim=8, client=c)
    with pytest.raises(ValueError, match="vector size 8"): QdrantIndex(dim=16, client=c)
