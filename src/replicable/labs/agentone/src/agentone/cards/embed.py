"""Embedders. HashEmbedder is deterministic + offline (tests, no key). OpenAIEmbedder is the real thing.
(Anthropic has no embeddings endpoint; pair Claude with OpenAI/Voyage/local embeddings.)"""
from __future__ import annotations
import hashlib, math, re
from typing import Protocol

class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

_STOP = {"the", "a", "an", "of", "to", "in", "is", "are", "and", "or", "what", "how", "does", "do", "it", "for", "that", "with", "as", "on", "by", "be"}

def tokens(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9_]+", t.lower()) if w not in _STOP]

class HashEmbedder:
    """Hashed bag-of-words. Lexical only (no semantics) -- fine for plumbing, weak for real retrieval."""
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
    def __init__(self, client=None, model: str = "text-embedding-3-small"):
        from openai import OpenAI
        self.client, self.model = client or OpenAI(), model
    def embed(self, texts):
        r = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in r.data]

def cosine(a: list[float], b: list[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0

def get_embedder(name: str) -> Embedder:
    return {"hash": HashEmbedder, "openai": OpenAIEmbedder}[name]()
