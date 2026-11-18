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
from fake_backends import fake_store

EMB = HashEmbedder()
def T(s, r, o): return Triple(subject=s, relation=r, object=o)

@pytest.fixture
def st():
    s = fake_store(EMB); load_seed(s, EMB); return s

# ---- pydantic ----
def test_score_bounds_and_triple_validation():
    with pytest.raises(ValidationError): Score(score=1.5, verdict="correct", feedback="x")
    with pytest.raises(ValidationError): T("  ", "r", "o")
    assert T(" a   b ", "r", "o").subject == "a b"

# ---- ingest: vector side + graph side + provenance ----
def test_ingest_embeds_and_builds_graph_with_provenance():
    st = fake_store(EMB)
    llm = FakeLLM({CardExtraction: [CardExtraction(triples=[T("Kafka", "feeds", "Atlas"), T("kafka", "is_a", "log")])]})
    c = ingest_card(st, llm, EMB, "What feeds Atlas?", "Kafka", card_id="x1")
    assert len(st.vector_of("x1")) == EMB.dim
    assert st.stats() == (3, 2)                                                      # kafka/Kafka deduped
    assert {r["card_id"] for r in st.edges()} == {"x1"} and st.get("x1").question == c.question

# ---- retrieval ----
def test_graph_mode_follows_entities_and_exclude_removes_edges(st):
    r = retrieve(st, EMB, "tell me about the checkpointer", mode="graph")
    assert r.cards and r.cards[0].id == "c3" and any("checkpointer" in f for f in r.facts)
    r2 = retrieve(st, EMB, "tell me about the checkpointer", mode="graph", exclude={"c3"})
    assert all(c.id != "c3" for c in r2.cards) and not any("thread_id" in f for f in r2.facts)  # no leaking edges

def test_retrieval_eval_runs(st):
    r = retrieval_eval(st, EMB)
    assert set(r) == {"vector", "graph", "hybrid"} and r["hybrid"] >= 0.5

# ---- session: routing guard, study card creation, exercise secrecy + scoring ----
def study(llm, st):
    return Session(build_session(st, llm, EMB), "study", "c3")

def test_study_ask_then_create_card_links_prerequisite(st):
    llm = FakeLLM({RouteDecision: [RouteDecision(intent="ask"), RouteDecision(intent="create_card")],
                   DraftCard: [DraftCard(question="What is graph state?", answer="The data passed between nodes.")],
                   CardExtraction: [CardExtraction(triples=[T("graph state", "passed_between", "nodes")])]},
                  texts=["State is what nodes read and write."])
    s = study(llm, st)
    assert "State is" in s.say("what is graph state?") and s.last_intent == "ask"
    out = s.say("make that a card")
    new = [c for c in st.cards() if c.prerequisite_of == "c3"]
    assert s.last_intent == "create_card" and len(new) == 1 and new[0].id in out
    assert st.vector_of(new[0].id) and st.triples_of(new[0].id)                      # embedded AND in the graph
    assert "Q: " + "How does LangGraph" in llm.log[1][1]                            # tutor saw the current card (study)

def test_mode_guard_coerces_disallowed_intents(st):
    llm = FakeLLM({RouteDecision: [RouteDecision(intent="submit_answer")]}, texts=["ok"])
    s = study(llm, st); s.say("anything"); assert s.last_intent == "ask"            # study can't submit
    llm = FakeLLM({RouteDecision: [RouteDecision(intent="create_card")]}, texts=["hint", "hint2"])
    ex = Session(build_session(st, llm, EMB), "exercise", "c3")
    ex.say("make a card"); assert ex.last_intent == "ask" and st.count() == 8  # exercise can't create cards
    ex.say("/card now"); assert ex.last_intent == "ask" and st.count() == 8   # slash-command is guarded too

def test_exercise_never_shows_answer_to_tutor_and_blocks_leaks(st):
    answer = st.get("c3").answer
    llm = FakeLLM({RouteDecision: [RouteDecision(intent="ask")]}, texts=[f"Sure: {answer}"])
    ex = Session(build_session(st, llm, EMB), "exercise", "c3")
    reply = ex.say("tell me the answer")
    system = llm.log[-1][1]
    assert answer not in system and "checkpointer saves" not in system             # tutor never received it
    assert "can't give that away" in reply                                           # and a leaked reply is replaced
    assert leaks("it is Kafka!", "Kafka") and not leaks("Kafkas", "Kafka")

def test_exercise_scoring_records_attempt_and_slash_bypasses_router(st):
    llm = FakeLLM({Score: [Score(score=0.9, verdict="correct", feedback="Nice.")]})  # no RouteDecision queued: router must not run
    ex = Session(build_session(st, llm, EMB), "exercise", "c3")
    out = ex.say("/answer a checkpointer saves state per thread id")
    assert ex.last_intent == "submit_answer" and "CORRECT (0.90)" in out and st.get("c3").answer in out
    assert st.attempts()[0].user_answer == "a checkpointer saves state per thread id" and st.mean_score("c3") == 0.9

def test_scheduler_prefers_unattempted_then_weakest(st):
    from agentone.cards.models import Attempt
    st.record(Attempt(card_id="c1", user_answer="x", score=0.2, verdict="incorrect", feedback=""))
    assert st.next_card("exercise").id != "c1"                      # unattempted cards first
    for c in st.cards():
        if c.id != "c1": st.record(Attempt(card_id=c.id, user_answer="x", score=0.9, verdict="correct", feedback=""))
    assert st.next_card("exercise").id == "c1"                      # now the weakest

# ---- facade behaviours (backends faked here; real ones are covered in test_integration.py) ----
def test_embedder_mismatch_is_refused():
    st = fake_store(EMB)
    with pytest.raises(ValueError, match="indexed with embedder 'hash'"):
        CardStore(st.pg, st.vec, st.graph, "openai:text-embedding-3-small")

def test_add_compensates_when_a_later_store_fails():
    st = fake_store(EMB); st.graph.fail = True
    with pytest.raises(RuntimeError):
        ingest_card(st, None, EMB, "q", "a", card_id="z", triples=[T("a", "r", "b")])
    assert not st.has("z") and st.vector_of("z") is None            # postgres + qdrant writes were undone

def test_graph_hops_widen_reach(st):
    one = {(r["subject"], r["object"]) for r in st.neighborhood(["checkpointer"], 1)}
    two = {(r["subject"], r["object"]) for r in st.neighborhood(["checkpointer"], 2)}
    assert ("LangGraph", "checkpointer") in one and ("checkpointer", "graph state") in one
    assert ("conditional edge", "LangGraph") not in one and ("conditional edge", "LangGraph") in two   # needs 2 hops
