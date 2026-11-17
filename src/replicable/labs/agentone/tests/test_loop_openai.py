import json
from agentone.loop_openai import run_agent
from fakes import FakeOpenAI

def test_openai_two_hop():
    c = FakeOpenAI(
        ("tool_calls", None, [("c1", "graph_search", json.dumps({"query": "Schema Registry"}))]),
        ("tool_calls", None, [("c2", "graph_search", json.dumps({"query": "Beacon"}))]),
        ("stop", "Carol Diaz", []),
    )
    r = run_agent("q", client=c)
    assert r.answer == "Carol Diaz" and r.steps == 3 and len(r.tool_calls) == 2
    tool_msg = c.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1"
    assert "Beacon --owns--> Schema Registry" in tool_msg["content"]

def test_bad_json_args_returned_as_error():
    c = FakeOpenAI(("tool_calls", None, [("c1", "calculator", "{oops")]), ("stop", "ok", []))
    run_agent("q", client=c)
    assert c.calls[1]["messages"][-1]["content"].startswith("ERROR: bad JSON")

def test_max_steps():
    c = FakeOpenAI(*[("tool_calls", None, [(f"c{i}", "calculator", '{"expression":"1+1"}')]) for i in range(3)])
    assert run_agent("q", client=c, max_steps=3).stop == "max_steps"
