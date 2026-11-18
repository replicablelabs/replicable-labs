"""CLI:  python -m agentone.cards.cli <command>
  doctor | seed | add Q A | list | graph | study [--card ID] | exercise [--card ID] | eval
Models/infra come from env vars (see config.py / .env.example)."""
import argparse
from .config import load_settings
from .deps import build_models, build_store
from .ingest import ingest_card
from .session import Session, build_session

def repl(session: Session, card, input_fn=input, print_fn=print) -> str:
    if session.mode == "study":
        print_fn(f"\n[STUDY] {card.id}\nQ: {card.question}\nA: {card.answer}\n"
                 "Ask questions. '/card' turns the topic into a new card. /next, /quit.")
    else:
        print_fn(f"\n[EXERCISE] {card.id}\nQ: {card.question}\n"
                 "Ask for hints. Submit with '/answer <your answer>'. /next, /quit.")
    while True:
        try: text = input_fn("> ").strip()
        except EOFError: return "quit"
        if not text: continue
        if text in ("/quit", "/q"): return "quit"
        if text == "/next": return "next"
        print_fn(session.say(text))

def run_mode(mode, store, llm, extractor, embedder, card_id=None, input_fn=input, print_fn=print):
    app = build_session(store, llm, embedder, extractor)
    seen: set[str] = set()
    while True:
        card = store.get(card_id) if card_id else store.next_card(mode, exclude=seen)
        if card is None: return print_fn("No cards left. Add some with `add` or `seed`.")
        seen.add(card.id)
        if repl(Session(app, mode, card.id), card, input_fn, print_fn) == "quit" or card_id: return

def doctor(s) -> int:
    print(f"inference : {s.inference.provider} / {s.inference.model}")
    print(f"extraction: {s.extraction.provider} / {s.extraction.model}")
    print(f"embedding : {s.embedding.provider} / {s.embedding.model} (dim {s.embedding.dim})")
    bad = 0
    def check(name, fn):
        nonlocal bad
        try: print(f"  OK   {name}: {fn()}")
        except Exception as e: bad += 1; print(f"  FAIL {name}: {type(e).__name__}: {str(e)[:140]}")
    import psycopg
    from qdrant_client import QdrantClient
    from neo4j import GraphDatabase
    check("postgres", lambda: psycopg.connect(s.infra.database_url, connect_timeout=3).execute("select version()").fetchone()[0][:40])
    check("qdrant  ", lambda: f"{len(QdrantClient(url=s.infra.qdrant_url, timeout=3).get_collections().collections)} collections")
    def neo():
        d = GraphDatabase.driver(s.infra.neo4j_uri, auth=(s.infra.neo4j_user, s.infra.neo4j_password)); d.verify_connectivity(); d.close(); return "connected"
    check("neo4j   ", neo)
    return 1 if bad else 0

def main(argv=None):
    p = argparse.ArgumentParser(prog="agentone.cards")
    sub = p.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add"); add.add_argument("question"); add.add_argument("answer")
    for m in ("study", "exercise"): sub.add_parser(m).add_argument("--card")
    for c in ("doctor", "seed", "list", "graph", "eval"): sub.add_parser(c)
    a = p.parse_args(argv)
    settings = load_settings()
    if a.cmd == "doctor": raise SystemExit(doctor(settings))
    store = build_store(settings); llm, extractor, emb = build_models(settings)

    if a.cmd == "seed":
        from .seed import load_seed; print(f"loaded {load_seed(store, emb)} cards")
    elif a.cmd == "list":
        for c in store.cards():
            m = store.mean_score(c.id); print(f"[{c.id}] {c.question}  (mean score: {'-' if m is None else f'{m:.2f}'})")
    elif a.cmd == "graph":
        n, e = store.stats(); print(f"{n} entities, {e} edges, {store.count()} cards")
        for r in store.edges(): print(f"  {r['subject']} --{r['relation']}--> {r['object']}  [{r['card_id']}]")
    elif a.cmd == "eval":
        from .evals import retrieval_eval
        print("retrieval recall@3 (over the stored deck):", retrieval_eval(store, emb))
    elif a.cmd == "add":
        c = ingest_card(store, extractor, emb, a.question, a.answer); print(f"added [{c.id}]")
    else:
        run_mode(a.cmd, store, llm, extractor, emb, a.card)

if __name__ == "__main__":
    main()
