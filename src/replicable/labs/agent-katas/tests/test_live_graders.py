"""Offline checks of the live-kata plumbing and graders (no API): graders accept good behaviour and reject bad behaviour,
and run_case wires the real loop + tools + world correctly using a scripted fake model."""
import pytest
from katas import cases as C
from katas.fakes import FakeClient, text, tool_use
from katas.live import run_case
from katas.k05_descriptions import solution as s5
from katas.k06_system_prompt import solution as s6
from katas.world import World

def T(calls, final="", world=None): return C.Trajectory(calls, final, "end_turn", world or World())
def case(cases, name): return next(c for c in cases if c.name == name)

def test_k05_graders():
    g = case(C.K05, "orders-by-email").grade
    assert g(T([("search_orders", {"query": "jane@example.com"})]))[0]
    assert not g(T([("lookup_order", {"order_id": "jane@example.com"})]))[0] and not g(T([]))[0]
    p = case(C.K05, "policy-question").grade
    assert p(T([("search_kb", {"query": "return policy"})]))[0] and not p(T([("lookup_order", {"order_id": "1"}), ("search_kb", {"query": "x"})]))[0]

def test_k06_graders_reject_the_classic_failures():
    w = World(); w.refunds["1002"] = [{"amount": 120.0, "reason": "x"}]
    assert not case(C.K06, "not-delivered").grade(T([("lookup_order", {})], "shipped", w))[0]          # refunded a shipped order
    assert case(C.K06, "not-delivered").grade(T([("lookup_order", {})], "It has only shipped so far."))[0]
    assert not case(C.K06, "missing-id").grade(T([("lookup_order", {"order_id": "1001"})], "?"))[0]   # guessed an id
    assert case(C.K06, "missing-id").grade(T([], "Which order number is it?"))[0]
    assert case(C.K06, "too-old").grade(T([("lookup_order", {})], "Refunds are limited to 30 days after delivery."))[0]
    assert case(C.K06, "over-amount").grade(T([("lookup_order", {})], "The most I can refund is $49.90."))[0]

def test_run_case_end_to_end_with_scripted_model():
    client = FakeClient(("tool_use", [tool_use("a", "lookup_order", order_id="1001")]),
                        ("tool_use", [tool_use("b", "issue_refund", order_id="1001", amount=24.95, reason="cracked")]),
                        ("end_turn", [text("Refunded R-1001-1.")]))
    c = case(C.K06, "eligible")
    t = run_case(c, s6.SCHEMAS, s6.SYSTEM, client)
    assert t.names() == ["lookup_order", "issue_refund"] and t.world.refunded("1001") == 24.95 and c.grade(t)[0]

def test_tool_errors_reach_the_model_as_is_error():
    client = FakeClient(("tool_use", [tool_use("a", "issue_refund", order_id="1002", amount=5, reason="x")]), ("end_turn", [text("no")]))
    run_case(case(C.K06, "not-delivered"), s6.SCHEMAS, s6.SYSTEM, client)
    res = client.calls[1]["messages"][-1]["content"][0]
    assert res["is_error"] is True and "shipped" in res["content"]

def test_k05_solution_schemas_are_wellformed_and_complete():
    names = {t["name"] for t in s5.SCHEMAS}
    assert names == {"lookup_order", "search_orders", "issue_refund", "search_kb"}
    for t in s5.SCHEMAS:
        assert len(t["description"]) > 60 and all("description" in p for p in t["input_schema"]["properties"].values())

def test_k06_company_specific_policy_graders():
    big = case(C.K06, "needs-human-approval").grade
    w = World(); w.refunds["1005"] = [{"amount": 200.0, "reason": "x"}]
    assert not big(T([("issue_refund", {})], "Done!", w))[0]
    assert big(T([("lookup_order", {})], "Refunds over $100 need approval, so a team member will follow up."))[0]
    sec = case(C.K06, "one-refund-per-order")
    w = World(); sec.setup(w); assert w.refunded("1001") == 10.0
    assert sec.grade(T([("lookup_order", {})], "That order was already refunded once.", w))[0]
    w.refunds["1001"].append({"amount": 10.0, "reason": "x"}); assert not sec.grade(T([], "ok", w))[0]
