"""Seed deck (agent/LLM-engineering topics) with pre-extracted triples, so it loads offline with no LLM."""
import json
from pathlib import Path
from .embed import Embedder
from .ingest import ingest_card
from .models import Triple
from .store import CardStore

SEED = Path(__file__).resolve().parents[3] / "data" / "seed_cards.json"

def load_seed(store: CardStore, embedder: Embedder, path: Path = SEED) -> int:
    n = 0
    for c in json.loads(path.read_text())["cards"]:
        if c["id"] in store.s.cards: continue
        ingest_card(store, None, embedder, c["question"], c["answer"], card_id=c["id"],
                    triples=[Triple(subject=s, relation=r, object=o) for s, r, o in c["triples"]]); n += 1
    return n

def retrieval_queries(path: Path = SEED) -> list[dict]:
    return json.loads(path.read_text())["retrieval_eval"]
