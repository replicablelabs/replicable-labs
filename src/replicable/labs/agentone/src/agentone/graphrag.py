"""Minimal GraphRAG: triples -> networkx graph -> entity-seeded k-hop retrieval.

Real GraphRAG (Microsoft) adds: LLM entity/relation extraction, Leiden community
detection, community summaries (global search) and entity-neighbourhood
retrieval (local search). Here: extraction is given (data/corpus.json), and we
implement LOCAL search by hand + a simple community (connected component) summary.
"""
from __future__ import annotations
import json, re
from pathlib import Path
import networkx as nx

DATA = Path(__file__).resolve().parents[2] / "data" / "corpus.json"


def load(path: Path = DATA) -> dict:
    return json.loads(path.read_text())


def build_graph(triples: list[list[str]]) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for s, r, o in triples:
        g.add_edge(s, o, relation=r)
    return g


def link_entities(g: nx.Graph, query: str) -> list[str]:
    """Entity linking: naive case-insensitive substring match. (Interview talking point: embeddings/LLM linking.)"""
    q = query.lower()
    return [n for n in g.nodes if n.lower() in q]


def neighborhood(g: nx.MultiDiGraph, seeds: list[str], hops: int = 2) -> list[tuple[str, str, str]]:
    """Return triples within `hops` of any seed (treating edges as undirected for reach)."""
    und = g.to_undirected(as_view=True)
    keep: set[str] = set()
    for s in seeds:
        keep |= set(nx.single_source_shortest_path_length(und, s, cutoff=hops))
    return sorted(
        {(u, d["relation"], v) for u, v, d in g.edges(data=True) if u in keep and v in keep}
    )


def retrieve(query: str, g: nx.MultiDiGraph, docs: list[dict], hops: int = 2) -> str:
    seeds = link_entities(g, query)
    if not seeds:  # fallback: lexical doc search
        words = set(re.findall(r"\w+", query.lower()))
        scored = sorted(docs, key=lambda d: -len(words & set(re.findall(r"\w+", d["text"].lower()))))
        return "\n".join(d["text"] for d in scored[:2])
    facts = neighborhood(g, seeds, hops)
    return "\n".join(f"{s} --{r}--> {o}" for s, r, o in facts)


def communities(g: nx.MultiDiGraph) -> list[list[str]]:
    """Global-search stand-in: greedy modularity communities (Leiden in real GraphRAG)."""
    from networkx.algorithms.community import greedy_modularity_communities
    return [sorted(c) for c in greedy_modularity_communities(g.to_undirected())]
