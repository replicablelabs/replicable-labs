"""All configuration comes from environment variables (loaded from <lab>/.env by `import agentone`).

Which model does which job -- one provider+model pair per role:

  INFERENCE_PROVIDER   anthropic | openai     tutor replies, intent router, card drafting, answer judge
  INFERENCE_MODEL
  EXTRACTION_PROVIDER  anthropic | openai     card -> knowledge-graph triples (nodes + edges)
  EXTRACTION_MODEL
  EMBEDDING_PROVIDER   openai | voyage | hash card text -> vector (hash = offline, tests only)
  EMBEDDING_MODEL
  EMBEDDING_DIM        only for models not in the known table

Infrastructure:  DATABASE_URL (Postgres)  QDRANT_URL  NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
Keys:            ANTHROPIC_API_KEY  OPENAI_API_KEY  VOYAGE_API_KEY  (read by the SDKs / embedders)
"""
from __future__ import annotations
import os
from typing import Literal, Mapping
from pydantic import BaseModel, Field

DEFAULT_MODELS = {
    ("inference", "openai"): "gpt-4.1", ("inference", "anthropic"): "claude-sonnet-5-5",
    ("extraction", "openai"): "gpt-4.1-mini", ("extraction", "anthropic"): "claude-haiku-5-5",
    ("embedding", "openai"): "text-embedding-3-small", ("embedding", "voyage"): "voyage-3.5",
    ("embedding", "hash"): "bag-of-words",
}
KNOWN_DIMS = {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072, "text-embedding-ada-002": 1536,
              "voyage-3.5": 1024, "voyage-3.5-lite": 1024, "voyage-3-large": 1024, "bag-of-words": 512}

class ChatModel(BaseModel):
    provider: Literal["anthropic", "openai"]
    model: str

class EmbeddingModel(BaseModel):
    provider: Literal["openai", "voyage", "hash"]
    model: str
    dim: int = Field(gt=0)
    @property
    def name(self) -> str: return "hash" if self.provider == "hash" else f"{self.provider}:{self.model}"

class Infra(BaseModel):
    database_url: str = "postgresql://localhost:5433/agentone"   # 5433: local Postgres started by scripts/services.sh
    qdrant_url: str = "http://localhost:6333"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "agentone-local"

class Settings(BaseModel):
    inference: ChatModel
    extraction: ChatModel
    embedding: EmbeddingModel
    infra: Infra = Infra()

def _chat(env: Mapping[str, str], role: str) -> ChatModel:
    p = env.get(f"{role.upper()}_PROVIDER", "openai").strip().lower()
    if p not in ("anthropic", "openai"):
        raise ValueError(f"{role.upper()}_PROVIDER must be 'anthropic' or 'openai', got {p!r}")
    return ChatModel(provider=p, model=env.get(f"{role.upper()}_MODEL") or DEFAULT_MODELS[(role, p)])

def _embedding(env: Mapping[str, str]) -> EmbeddingModel:
    p = env.get("EMBEDDING_PROVIDER", "openai").strip().lower()
    if p == "anthropic":
        raise ValueError("Anthropic has no embeddings API. Set EMBEDDING_PROVIDER=openai, or voyage (Anthropic's recommended "
                         "embeddings provider; needs VOYAGE_API_KEY).")
    if p not in ("openai", "voyage", "hash"):
        raise ValueError(f"EMBEDDING_PROVIDER must be openai | voyage | hash, got {p!r}")
    model = env.get("EMBEDDING_MODEL") or DEFAULT_MODELS[("embedding", p)]
    dim = env.get("EMBEDDING_DIM") or KNOWN_DIMS.get(model)
    if dim is None: raise ValueError(f"Unknown embedding model {model!r}: set EMBEDDING_DIM")
    return EmbeddingModel(provider=p, model=model, dim=int(dim))

def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    d = Infra()
    infra = Infra(database_url=env.get("DATABASE_URL", d.database_url), qdrant_url=env.get("QDRANT_URL", d.qdrant_url),
                  neo4j_uri=env.get("NEO4J_URI", d.neo4j_uri), neo4j_user=env.get("NEO4J_USER", d.neo4j_user),
                  neo4j_password=env.get("NEO4J_PASSWORD", d.neo4j_password))
    return Settings(inference=_chat(env, "inference"), extraction=_chat(env, "extraction"),
                    embedding=_embedding(env), infra=infra)
