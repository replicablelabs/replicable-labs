"""Run against the REAL servers (Postgres, Qdrant, Neo4j). Skipped automatically when they are not reachable.
Uses throwaway names (own PG schema search_path, own Qdrant collection, :ItTest-prefixed card ids) and cleans up after itself,
so it never touches your real cards. Start servers:  scripts/services.sh start"""
import socket, uuid
from urllib.parse import urlparse
import pytest
from agentone.cards.config import load_settings
from agentone.cards.embed import HashEmbedder
from agentone.cards.graph import Neo4jGraph
from agentone.cards.models import Attempt, Card, Triple
from agentone.cards.pg import PostgresCards
from agentone.cards.store import CardStore
from agentone.cards.vectors import QdrantIndex

S = load_settings()
def _up(url: str, default_port: int) -> bool:
    u = urlparse(url if "://" in url else f"//{url}")
    try: socket.create_connection((u.hostname or "localhost", u.port or default_port), timeout=0.5).close(); return True
    except OSError: return False

pytestmark = pytest.mark.skipif(
    not (_up(S.infra.database_url, 5433) and _up(S.infra.qdrant_url, 6333) and _up(S.infra.neo4j_uri, 7687)),
    reason="postgres/qdrant/neo4j not all reachable (run scripts/services.sh start)")

E = HashEmbedder()

@pytest.fixture
def store():
    tag = uuid.uuid4().hex[:6]
    import psycopg
    schema = f"it_{tag}"
    admin = psycopg.connect(S.infra.database_url, autocommit=True); admin.execute(f"create schema {schema}")
    sep = "&" if "?" in S.infra.database_url else "?"
    pg = PostgresCards(f"{S.infra.database_url}{sep}options=-csearch_path%3D{schema}")
    vec = QdrantIndex(S.infra.qdrant_url, E.dim, collection=f"it_{tag}")
    g = Neo4jGraph(S.infra.neo4j_uri, S.infra.neo4j_user, S.infra.neo4j_password)
    st = CardStore(pg, vec, g, E.name); st.tag = tag
    yield st
    for c in st.cards(): g.delete_card(c.id)
    vec.c.delete_collection(vec.collection); pg.close(); admin.execute(f"drop schema {schema} cascade"); admin.close(); vec.close(); g.close()

def T(s, r, o): return Triple(subject=s, relation=r, object=o)

def test_roundtrip_across_all_three_stores(store):
    t = store.tag
    for cid, q, a, ts in [(f"{t}a", "what does the checkpointer save", "graph state", [T("LangGraph", "uses", f"checkpointer{t}"), T(f"checkpointer{t}", "saves", "graph state")]),
                          (f"{t}b", "what is a conditional edge", "runtime routing", [T("conditional edge", "part_of", "LangGraph")])]:
        from agentone.cards.ingest import ingest_card
        ingest_card(store, None, E, q, a, card_id=cid, triples=ts)
    assert store.count() == 2 and len(store.vector_of(f"{t}a")) == E.dim
    # vector search
    assert store.search(E.embed(["checkpointer save"])[0], 1)[0][0].id == f"{t}a"
    assert store.search(E.embed(["checkpointer save"])[0], 1, exclude=[f"{t}a"])[0][0].id == f"{t}b"
    # graph: link + k-hop widening + exclusion
    assert store.link_entities(f"tell me about checkpointer{t}") == [f"checkpointer{t}"]
    one = {(r["subject"], r["object"]) for r in store.neighborhood([f"checkpointer{t}"], 1)}
    two = {(r["subject"], r["object"]) for r in store.neighborhood([f"checkpointer{t}"], 2)}
    assert ("LangGraph", f"checkpointer{t}") in one and ("conditional edge", "LangGraph") not in one and ("conditional edge", "LangGraph") in two
    assert not store.neighborhood([f"checkpointer{t}"], 2, exclude=[f"{t}a", f"{t}b"])
    assert store.triples_of(f"{t}b")[0].subject == "conditional edge"
    # relational: attempts + scheduler
    store.record(Attempt(card_id=f"{t}a", user_answer="x", score=0.4, verdict="partial", feedback="f"))
    assert store.mean_score(f"{t}a") == pytest.approx(0.4) and store.next_card("exercise").id == f"{t}b"
    # embedder pin persisted in postgres
    with pytest.raises(ValueError, match="indexed with embedder"): CardStore(store.pg, store.vec, store.graph, "openai:other")

def test_add_rolls_back_when_graph_write_fails(store):
    store.graph.add_triples = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        store.add(Card(id=f"{store.tag}z", question="q", answer="a"), E.embed(["q"])[0], [T("a", "r", "b")])
    assert not store.has(f"{store.tag}z") and store.vector_of(f"{store.tag}z") is None
