"""Embedders. HashEmbedder is deterministic + offline (tests, no key). OpenAIEmbedder is the real thing.
(Anthropic has no embeddings endpoint; pair Claude with OpenAI/Voyage/local embeddings.)"""
from __future__ import annotations
import hashlib, math, re
from typing import Protocol

class Embedder(Protocol):
    name: str
    dim: int
    def embed(self, texts: list[str]) -> list[list[float]]: ...

_STOP = {"the", "a", "an", "of", "to", "in", "is", "are", "and", "or", "what", "how", "does", "do", "it", "for", "that", "with", "as", "on", "by", "be"}

def tokens(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9_]+", t.lower()) if w not in _STOP]

class HashEmbedder:
    """Hashed bag-of-words. Lexical only (no semantics) -- fine for plumbing, weak for real retrieval."""
    name = "hash"
    def __init__(self, dim: int = 512): self.dim = dim
    def embed(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for w in tokens(t): v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dim] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out

class OpenAIEmbedder:
    def __init__(self, model: str, dim: int, client=None):
        from openai import OpenAI
        self.client, self.model, self.dim, self.name = client or OpenAI(), model, dim, f"openai:{model}"
    def embed(self, texts):
        kw = {"dimensions": self.dim} if self.model.startswith("text-embedding-3") else {}
        r = self.client.embeddings.create(model=self.model, input=texts, **kw)
        return [d.embedding for d in sorted(r.data, key=lambda d: d.index)]

class VoyageEmbedder:
    """Voyage AI (Anthropic's recommended embeddings provider). Plain REST; needs VOYAGE_API_KEY."""
    URL = "https://api.voyageai.com/v1/embeddings"
    def __init__(self, model: str, dim: int):
        self.model, self.dim, self.name = model, dim, f"voyage:{model}"
    def embed(self, texts):
        import httpx, os
        r = httpx.post(self.URL, json={"input": texts, "model": self.model, "output_dimension": self.dim},
                       headers={"Authorization": f"Bearer {os.environ['VOYAGE_API_KEY']}"}, timeout=60)
        r.raise_for_status()
        return [d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])]

def cosine(a: list[float], b: list[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0

def get_embedder(role) -> Embedder:
    """role: config.EmbeddingModel."""
    if role.provider == "hash": return HashEmbedder(role.dim)
    return {"openai": OpenAIEmbedder, "voyage": VoyageEmbedder}[role.provider](role.model, role.dim)
