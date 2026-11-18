from katas.fakes import FakeClient, text, tool_use
from katas.loader import load

M = load("k01_loop")
SCHEMAS = [{"name": "echo", "description": "Echo text uppercased.", "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}]
IMPLS = {"echo": lambda text: text.upper()}

def run(client, impls=IMPLS, **kw): return M.run_agent("q", client, SCHEMAS, impls, **kw)

def test_single_tool_roundtrip():
    c = FakeClient(("tool_use", [tool_use("t1", "echo", text="hi")]), ("end_turn", [text("done")]))
    r = run(c)
    assert (r.answer, r.steps, r.stop) == ("done", 2, "end_turn")
    assert c.calls[1]["messages"][-1]["content"][0]["content"] == "HI"

def test_parallel_tool_calls_answered_in_one_user_message():
    c = FakeClient(("tool_use", [tool_use("a", "echo", text="x"), tool_use("b", "echo", text="y")]), ("end_turn", [text("ok")]))
    run(c)
    last = c.calls[1]["messages"][-1]
    assert [b["tool_use_id"] for b in last["content"]] == ["a", "b"]

def test_text_before_tool_use_is_preserved_and_answer_uses_all_text():
    c = FakeClient(("tool_use", [text("Let me check."), tool_use("a", "echo", text="x")]), ("end_turn", [text("It is "), text("X.")]))
    assert run(c).answer == "It is X."

def test_unknown_tool_becomes_error_result_not_crash():
    c = FakeClient(("tool_use", [tool_use("a", "nope")]), ("end_turn", [text("sorry")]))
    r = run(c)
    res = c.calls[1]["messages"][-1]["content"][0]
    assert r.answer == "sorry" and res["is_error"] is True and "nope" in res["content"]

def test_tool_exception_becomes_error_result_not_crash():
    def boom(text): raise ValueError("boom")
    c = FakeClient(("tool_use", [tool_use("a", "echo", text="x")]), ("end_turn", [text("sorry")]))
    r = run(c, impls={"echo": boom})
    res = c.calls[1]["messages"][-1]["content"][0]
    assert r.answer == "sorry" and res["is_error"] is True and "boom" in res["content"]

def test_max_steps_is_enforced():
    c = FakeClient(("tool_use", [tool_use("a", "echo", text="x")]), repeat_last=True)
    r = run(c, max_steps=3)
    assert r.stop == "max_steps" and len(c.calls) == 3

def test_returns_model_stop_reason_and_passes_system_and_tools():
    c = FakeClient(("max_tokens", [text("cut off")]))
    r = run(c, system="sys")
    assert r.stop == "max_tokens" and r.answer == "cut off"
    assert c.calls[0]["system"] == "sys" and c.calls[0]["tools"] == SCHEMAS
