"""In-memory stand-ins for the three real backends (same interfaces as pg.py / vectors.py / graph.py).
Used ONLY by unit tests so they run with no servers; the app itself never uses these."""
import math, re
from agentone.cards.embed import cosine
from agentone.cards.models import Attempt, Card, Triple
from agentone.cards.store import CardStore

class FakeCards:
    def __init__(self): self.cards, self.att, self.meta = {}, [], {}
    def close(self): pass
    def get_meta(self, k): return self.meta.get(k)
    def set_meta(self, k, v): self.meta[k] = v
    def add(self, c):
        if c.id in self.cards: raise ValueError("duplicate")
        self.cards[c.id] = c
    def delete(self, i): self.cards.pop(i, None)
    def has(self, i): return i in self.cards
    def get(self, i): return self.cards[i]
    def all(self): return sorted(self.cards.values(), key=lambda c: (c.created_at, c.id))
    def count(self): return len(self.cards)
    def record(self, a): self.att.append(a)
    def attempts(self, cid=None): return [a for a in self.att if cid in (None, a.card_id)]
    def mean_score(self, cid):
        xs = [a.score for a in self.att if a.card_id == cid]; return sum(xs) / len(xs) if xs else None
    def next_card(self, mode, exclude=()):
        cs = [c for c in self.all() if c.id not in exclude]
        if not cs: return None
        if mode == "study": return cs[0]
        return min(cs, key=lambda c: (-1.0 if self.mean_score(c.id) is None else self.mean_score(c.id), c.created_at, c.id))

class FakeVectors:
    def __init__(self): self.v = {}
    def close(self): pass
    def upsert(self, card, vec): self.v[card.id] = vec
    def delete(self, cid): self.v.pop(cid, None)
    def search(self, vec, k, exclude=()):
        s = sorted(((i, cosine(vec, x)) for i, x in self.v.items() if i not in exclude), key=lambda t: (-t[1], t[0])); return s[:k]
    def vector_of(self, cid): return self.v.get(cid)

class FakeGraph:
    def __init__(self): self.rows, self.fail = [], False   # rows: dict(subject, relation, object, card_id, subject_key, object_key)
    def close(self): pass
    def add_triples(self, cid, ts):
        if self.fail: raise RuntimeError("neo4j down")
        self.rows += [dict(subject=t.subject, relation=t.relation, object=t.object, card_id=cid,
                           subject_key=t.subject.lower(), object_key=t.object.lower()) for t in ts]
    def delete_card(self, cid): self.rows = [r for r in self.rows if r["card_id"] != cid]
    def _live(self, ex): return [r for r in self.rows if r["card_id"] not in ex]
    def link_entities(self, q, exclude=()):
        q = q.lower(); keys = {r[k] for r in self._live(exclude) for k in ("subject_key", "object_key")}
        return sorted(k for k in keys if re.search(rf"(?<!\w){re.escape(k)}(?!\w)", q))
    def neighborhood(self, seeds, hops, exclude=()):
        live = self._live(exclude); reach = set(seeds); frontier = set(seeds)
        for _ in range(hops):
            frontier = {r["object_key"] if r["subject_key"] in frontier else r["subject_key"]
                        for r in live if r["subject_key"] in frontier or r["object_key"] in frontier} - reach
            reach |= frontier
        return sorted((r for r in live if r["subject_key"] in reach and r["object_key"] in reach),
                      key=lambda r: (r["card_id"], r["subject_key"], r["relation"], r["object_key"]))
    def stats(self): return len({k for r in self.rows for k in (r["subject_key"], r["object_key"])}), len(self.rows)
    def edges(self): return sorted(self.rows, key=lambda r: r["card_id"])
    def triples_of(self, cid): return [Triple(subject=r["subject"], relation=r["relation"], object=r["object"]) for r in self.rows if r["card_id"] == cid]

def fake_store(embedder) -> CardStore:
    return CardStore(FakeCards(), FakeVectors(), FakeGraph(), embedder.name)
