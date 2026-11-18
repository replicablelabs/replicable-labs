"""Wire settings -> concrete stores / models. The only place that knows about real servers."""
from .config import Settings
from .embed import get_embedder
from .graph import Neo4jGraph
from .llm import get_llm
from .pg import PostgresCards
from .store import CardStore
from .vectors import QdrantIndex

def build_store(s: Settings) -> CardStore:
    i, e = s.infra, s.embedding
    return CardStore(PostgresCards(i.database_url), QdrantIndex(i.qdrant_url, e.dim),
                     Neo4jGraph(i.neo4j_uri, i.neo4j_user, i.neo4j_password), e.name)

def build_models(s: Settings):
    """-> (inference LLM, extraction LLM, embedder)"""
    return get_llm(s.inference), get_llm(s.extraction), get_embedder(s.embedding)
