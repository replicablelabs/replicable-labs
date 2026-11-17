import pytest
from pydantic import ValidationError
from agentone.cards.embed import HashEmbedder
from agentone.cards.evals import retrieval_eval
from agentone.cards.ingest import ingest_card
from agentone.cards.models import CardExtraction, DraftCard, RouteDecision, Score, Triple
from agentone.cards.retrieve import retrieve
from agentone.cards.seed import load_seed
from agentone.cards.session import Session, build_session, leaks
from agentone.cards.store import CardStore
from fakes import FakeLLM

EMB = HashEmbedder()
def T(s, r, o): return Triple(subject=s, relation=r, object=o)

def seeded():
    st = CardStore(); load_seed(st, EMB); return st

# ---- pydantic ----
def test_score_bounds_and_triple_validation():
    with pytest.raises(ValidationError): Score(score=1.5, verdict="correct", feedback="x")
    with pytest.raises(ValidationError): T("  ", "r", "o")
    assert T(" a   b ", "r", "o").subject == "a b"

# ---- ingest: vector side + graph side + provenance ----
def test_ingest_embeds_and_builds_graph_with_provenance(tmp_path):
    st = CardStore(tmp_path / "db.json")
    llm = FakeLLM({CardExtraction: [CardExtraction(triples=[T("Kafka", "feeds", "Atlas"), T("kafka", "is_a", "log")])]})
    c = ingest_card(st, llm, EMB, "What feeds Atlas?", "Kafka", card_id="x1")
    assert len(st.s.vectors["x1"]) == EMB.dim
    g = st.graph()
    assert g.number_of_nodes() == 3 and g.nodes["kafka"]["label"] == "Kafka"      # case-insensitive dedupe
    assert {d["card_id"] for *_, d in g.edges(data=True)} == {"x1"}
    st2 = CardStore(tmp_path / "db.json")                                            # persistence round-trip
    assert st2.get("x1").question == c.question and len(st2.graph().edges) == 2

# ---- retrieval ----
def test_graph_mode_follows_entities_and_exclude_removes_edges():
    st = seeded()
    r = retrieve(st, EMB, "tell me about the checkpointer", mode="graph")
    assert r.cards and r.cards[0].id == "c3" and any("checkpointer" in f for f in r.facts)
    r2 = retrieve(st, EMB, "tell me about the checkpointer", mode="graph", exclude={"c3"})
    assert all(c.id != "c3" for c in r2.cards) and not any("thread_id" in f for f in r2.facts)  # no leaking edges

def test_retrieval_eval_runs():
    r = retrieval_eval(EMB)
    assert set(r) == {"vector", "graph", "hybrid"} and r["hybrid"] >= 0.5

# ---- session: routing guard, study card creation, exercise secrecy + scoring ----
def study(llm, st=None):
    st = st or seeded(); return st, Session(build_session(st, llm, EMB), "study", "c3")

def test_study_ask_then_create_card_links_prerequisite():
    llm = FakeLLM({RouteDecision: [RouteDecision(intent="ask"), RouteDecision(intent="create_card")],
                   DraftCard: [DraftCard(question="What is graph state?", answer="The data passed between nodes.")],
                   CardExtraction: [CardExtraction(triples=[T("graph state", "passed_between", "nodes")])]},
                  texts=["State is what nodes read and write."])
    st, s = study(llm)
    assert "State is" in s.say("what is graph state?") and s.last_intent == "ask"
    out = s.say("make that a card")
    new = [c for c in st.s.cards.values() if c.prerequisite_of == "c3"]
    assert s.last_intent == "create_card" and len(new) == 1 and new[0].id in out
    assert new[0].id in st.s.vectors and st.s.triples[new[0].id]                    # embedded AND in the graph
    assert "Q: " + "How does LangGraph" in llm.log[1][1]                            # tutor saw the current card (study)

def test_mode_guard_coerces_disallowed_intents():
    llm = FakeLLM({RouteDecision: [RouteDecision(intent="submit_answer")]}, texts=["ok"])
    _, s = study(llm); s.say("anything"); assert s.last_intent == "ask"            # study can't submit
    llm = FakeLLM({RouteDecision: [RouteDecision(intent="create_card")]}, texts=["hint", "hint2"])
    st = seeded(); ex = Session(build_session(st, llm, EMB), "exercise", "c3")
    ex.say("make a card"); assert ex.last_intent == "ask" and len(st.s.cards) == 8  # exercise can't create cards
    ex.say("/card now"); assert ex.last_intent == "ask" and len(st.s.cards) == 8   # slash-command is guarded too

def test_exercise_never_shows_answer_to_tutor_and_blocks_leaks():
    st = seeded(); answer = st.get("c3").answer
    llm = FakeLLM({RouteDecision: [RouteDecision(intent="ask")]}, texts=[f"Sure: {answer}"])
    ex = Session(build_session(st, llm, EMB), "exercise", "c3")
    reply = ex.say("tell me the answer")
    system = llm.log[-1][1]
    assert answer not in system and "checkpointer saves" not in system             # tutor never received it
    assert "can't give that away" in reply                                           # and a leaked reply is replaced
    assert leaks("it is Kafka!", "Kafka") and not leaks("Kafkas", "Kafka")

def test_exercise_scoring_records_attempt_and_slash_bypasses_router():
    st = seeded()
    llm = FakeLLM({Score: [Score(score=0.9, verdict="correct", feedback="Nice.")]})  # no RouteDecision queued: router must not run
    ex = Session(build_session(st, llm, EMB), "exercise", "c3")
    out = ex.say("/answer a checkpointer saves state per thread id")
    assert ex.last_intent == "submit_answer" and "CORRECT (0.90)" in out and st.get("c3").answer in out
    assert st.s.attempts[0].user_answer == "a checkpointer saves state per thread id" and st.mean_score("c3") == 0.9

def test_scheduler_prefers_unattempted_then_weakest():
    st = seeded(); from agentone.cards.models import Attempt
    st.record(Attempt(card_id="c1", user_answer="x", score=0.2, verdict="incorrect", feedback=""))
    assert st.next_card("exercise").id != "c1"                      # unattempted cards first
    for cid in list(st.s.cards):
        if cid != "c1": st.record(Attempt(card_id=cid, user_answer="x", score=0.9, verdict="correct", feedback=""))
    assert st.next_card("exercise").id == "c1"                      # now the weakest
