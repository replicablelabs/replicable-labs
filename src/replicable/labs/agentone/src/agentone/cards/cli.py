"""CLI:  python -m agentone.cards.cli [--provider anthropic|openai] [--embedder hash|openai] <command>
  seed | add Q A | list | graph | study [--card ID] | exercise [--card ID] | eval"""
import argparse, os
from pathlib import Path
from .embed import get_embedder
from .ingest import ingest_card
from .session import Session, build_session
from .store import CardStore

DEFAULT_DB = Path(__file__).resolve().parents[3] / "data" / "cards.db"

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

def run_mode(mode, store, llm, embedder, card_id=None, input_fn=input, print_fn=print):
    app = build_session(store, llm, embedder)
    seen: set[str] = set()
    while True:
        card = store.get(card_id) if card_id else store.next_card(mode, exclude=seen)
        if card is None: return print_fn("No cards left. Add some with `add` or `seed`.")
        seen.add(card.id)
        if repl(Session(app, mode, card.id), card, input_fn, print_fn) == "quit" or card_id: return

def main(argv=None):
    p = argparse.ArgumentParser(prog="agentone.cards")
    p.add_argument("--provider", default=os.environ.get("AGENTONE_PROVIDER", "anthropic"), choices=["anthropic", "openai"])
    p.add_argument("--embedder", default=os.environ.get("AGENTONE_EMBEDDER", "hash"), choices=["hash", "openai"])
    p.add_argument("--db", type=Path, default=Path(os.environ.get("AGENTONE_DB", DEFAULT_DB)))
    sub = p.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add"); add.add_argument("question"); add.add_argument("answer")
    for m in ("study", "exercise"): sub.add_parser(m).add_argument("--card")
    for c in ("seed", "list", "graph", "eval"): sub.add_parser(c)
    a = p.parse_args(argv)
    emb = get_embedder(a.embedder); store = CardStore(a.db, emb.name, emb.dim)

    if a.cmd == "seed":
        from .seed import load_seed; print(f"loaded {load_seed(store, emb)} cards")
    elif a.cmd == "list":
        for c in store.cards():
            m = store.mean_score(c.id); print(f"[{c.id}] {c.question}  (mean score: {'-' if m is None else f'{m:.2f}'})")
    elif a.cmd == "graph":
        n, e = store.stats(); print(f"{n} entities, {e} edges, {store.count()} cards  ({a.db})")
        for r in store.edges(): print(f"  {r['subject']} --{r['relation']}--> {r['object']}  [{r['card_id']}]")
    elif a.cmd == "eval":
        from .evals import retrieval_eval
        print("retrieval recall@3:", retrieval_eval(emb))
    else:
        from .llm import get_llm
        llm = get_llm(a.provider)
        if a.cmd == "add":
            c = ingest_card(store, llm, emb, a.question, a.answer); print(f"added [{c.id}]")
        else:
            run_mode(a.cmd, store, llm, emb, a.card)

if __name__ == "__main__":
    main()
