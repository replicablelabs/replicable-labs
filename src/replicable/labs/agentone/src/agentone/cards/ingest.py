"""Ingest = embed the card (vector side) + extract triples (graph side) + persist both."""
from .embed import Embedder
from .llm import LLM
from .models import Card, CardExtraction, Triple
from .store import CardStore

EXTRACT_SYSTEM = ("Extract knowledge-graph triples from a flashcard. Each triple is (subject, relation, object): "
                  "subject/object are short noun-phrase entities (reuse common names: 'LangGraph', not 'the framework'); "
                  "relation is a short snake_case verb phrase. Only facts stated by the card.")

def card_text(question: str, answer: str) -> str: return f"Q: {question}\nA: {answer}"

def ingest_card(store: CardStore, llm: LLM | None, embedder: Embedder, question: str, answer: str, *,
                prerequisite_of: str | None = None, card_id: str | None = None,
                triples: list[Triple] | None = None) -> Card:
    card = Card(question=question, answer=answer, prerequisite_of=prerequisite_of, **({"id": card_id} if card_id else {}))
    if triples is None:
        triples = llm.structured(EXTRACT_SYSTEM, card_text(question, answer), CardExtraction).triples
    store.add(card, embedder.embed([card_text(question, answer)])[0], triples)
    return card
