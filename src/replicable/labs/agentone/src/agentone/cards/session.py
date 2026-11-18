r"""The session graph (LangGraph). One graph, two modes:

  START -> route --ask-----------> ask ------------> END
                 \--create_card--> create_card ----> END     (study only)
                  \-submit_answer> score ----------> END     (exercise only)

route = deterministic slash-commands first, else an LLM intent classifier (pydantic RouteDecision), then a hard
mode guard: an intent not allowed in the current mode is coerced to "ask". Safety lives in code, not in the prompt.
"""
import operator, re, uuid
from typing import Annotated, TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from .embed import Embedder
from .ingest import ingest_card
from .llm import LLM
from .models import Attempt, DraftCard, RouteDecision, Score
from .retrieve import retrieve
from .store import CardStore

ALLOWED = {"study": {"ask", "create_card"}, "exercise": {"ask", "submit_answer"}}

ROUTE_SYSTEM = {
    "study": "Classify the learner's message. ask = a question or request for explanation. "
             "create_card = they want a new flashcard made from this topic/question. Return the intent.",
    "exercise": "Classify the learner's message. ask = a question or request for a hint. "
                "submit_answer = they are stating their final answer to the card's question. Return the intent.",
}
STUDY_SYSTEM = ("You are a tutor helping a learner study ONE flashcard so they can learn its answer.\n"
                "Card:\nQ: {q}\nA: {a}\n\nRelated cards:\n{cards}\n\nRelated facts:\n{facts}\n\n"
                "Answer the learner's questions concisely, aimed at understanding the card's answer.")
EXERCISE_SYSTEM = ("You coach a learner practising this flashcard question: {q}\n"
                   "You do NOT know the expected answer. Never state or guess a final answer. Give hints and "
                   "explain concepts using only this context.\n\nRelated cards:\n{cards}\n\nRelated facts:\n{facts}")
DRAFT_SYSTEM = ("Draft ONE new flashcard (question + answer) that the learner needs to understand the current card. "
                "Base it on their request and the conversation. Question must be self-contained; answer concise.")
JUDGE_SYSTEM = ("Grade a learner's answer against the expected answer. Judge meaning, not wording. "
                "correct (score ~1.0) = same key facts; partial (0.3-0.7) = some key facts; incorrect (<0.3). "
                "feedback: one or two sentences, no new facts beyond the expected answer.")
LEAK_REPLY = "I can't give that away. Try asking about a related concept, or state your answer with /answer."

def _norm(s: str) -> str: return " ".join(re.findall(r"[a-z0-9_]+", s.lower()))

def leaks(reply: str, answer: str) -> bool:
    a = _norm(answer)
    return bool(a) and re.search(rf"(?<!\w){re.escape(a)}(?!\w)", _norm(reply)) is not None

class State(TypedDict, total=False):
    mode: str
    card_id: str
    user_input: str
    answer_text: str
    intent: str
    reply: str
    history: Annotated[list, operator.add]   # reducer: nodes append, checkpointer keeps it per thread

def build_session(store: CardStore, llm: LLM, embedder: Embedder, extractor: LLM | None = None, checkpointer=None):
    """llm = INFERENCE model (router, tutor, drafting, judge); extractor = EXTRACTION model (card -> triples)."""
    extractor = extractor or llm
    def context(query: str, card_id: str) -> tuple[str, str]:
        r = retrieve(store, embedder, query, k=3, exclude={card_id})  # never retrieve the card at hand
        return ("\n".join(f"- Q: {c.question} A: {c.answer}" for c in r.cards) or "(none)",
                "\n".join(r.facts) or "(none)")

    def route(state: State):
        text, mode = state["user_input"].strip(), state["mode"]
        answer_text = text
        if text.startswith("/answer"): intent, answer_text = "submit_answer", text[len("/answer"):].strip()
        elif text.startswith("/card"): intent = "create_card"
        else: intent = llm.structured(ROUTE_SYSTEM[mode], text, RouteDecision).intent
        if intent not in ALLOWED[mode]: intent = "ask"
        return {"intent": intent, "answer_text": answer_text, "history": [{"role": "user", "content": text}]}

    def ask(state: State):
        card = store.get(state["card_id"])
        cards, facts = context(state["user_input"], card.id)
        if state["mode"] == "study":
            system = STUDY_SYSTEM.format(q=card.question, a=card.answer, cards=cards, facts=facts)
        else:
            system = EXERCISE_SYSTEM.format(q=card.question, cards=cards, facts=facts)
        reply = llm.text(system, state["history"][-10:])
        if state["mode"] == "exercise" and leaks(reply, card.answer): reply = LEAK_REPLY  # defence in depth
        return {"reply": reply, "history": [{"role": "assistant", "content": reply}]}

    def create_card(state: State):
        card = store.get(state["card_id"])
        convo = "\n".join(f"{m['role']}: {m['content']}" for m in state["history"][-6:])
        draft = llm.structured(DRAFT_SYSTEM, f"Current card:\nQ: {card.question}\nA: {card.answer}\n\n"
                                             f"Conversation:\n{convo}", DraftCard)
        new = ingest_card(store, extractor, embedder, draft.question, draft.answer, prerequisite_of=card.id)
        reply = f"Created card [{new.id}] (prerequisite of {card.id}):\nQ: {new.question}\nA: {new.answer}"
        return {"reply": reply, "history": [{"role": "assistant", "content": reply}]}

    def score(state: State):
        card = store.get(state["card_id"])
        s = llm.structured(JUDGE_SYSTEM, f"Question: {card.question}\nExpected answer: {card.answer}\n"
                                         f"Learner's answer: {state['answer_text']}", Score)
        store.record(Attempt(card_id=card.id, user_answer=state["answer_text"], score=s.score,
                             verdict=s.verdict, feedback=s.feedback))
        reply = f"{s.verdict.upper()} ({s.score:.2f}): {s.feedback}\nExpected: {card.answer}"
        return {"reply": reply, "history": [{"role": "assistant", "content": reply}]}

    g = StateGraph(State)
    for name, fn in [("route", route), ("ask", ask), ("create_card", create_card), ("score", score)]: g.add_node(name, fn)
    g.add_edge(START, "route")
    g.add_conditional_edges("route", lambda s: s["intent"], {"ask": "ask", "create_card": "create_card", "submit_answer": "score"})
    for n in ("ask", "create_card", "score"): g.add_edge(n, END)
    return g.compile(checkpointer=checkpointer or MemorySaver())

class Session:
    """One study/exercise session on one card (a LangGraph thread)."""
    def __init__(self, app, mode: str, card_id: str, thread_id: str | None = None):
        self.app, self.mode, self.card_id = app, mode, card_id
        self.thread_id = thread_id or uuid.uuid4().hex
        self.last_intent: str | None = None
    def say(self, text: str) -> str:
        out = self.app.invoke({"mode": self.mode, "card_id": self.card_id, "user_input": text},
                              {"configurable": {"thread_id": self.thread_id}})
        self.last_intent = out["intent"]
        return out["reply"]
