from agentone.loop import run_agent
from agentone import graphrag, tools
from fakes import FakeClient, text, tool_use

def test_two_hop_loop():
    c = FakeClient(
        ("tool_use", [tool_use("t1", "graph_search", query="Schema Registry")]),
        ("tool_use", [tool_use("t2", "graph_search", query="Beacon")]),
        ("end_turn", [text("Carol Diaz")]),
    )
    r = run_agent("Who leads the team that owns the Schema Registry?", client=c)
    assert r.answer == "Carol Diaz" and r.steps == 3 and len(r.tool_calls) == 2
    # tool_result went back as a single user message with matching id
    last_user = c.calls[1]["messages"][-1]
    assert last_user["role"] == "user" and last_user["content"][0]["tool_use_id"] == "t1"
    assert "Beacon --owns--> Schema Registry" in last_user["content"][0]["content"]

def test_tool_error_returned_not_raised():
    c = FakeClient(("tool_use", [tool_use("t1", "calculator", expression="import os")]), ("end_turn", [text("sorry")]))
    r = run_agent("x", client=c)
    assert c.calls[1]["messages"][-1]["content"][0]["is_error"] is True

def test_max_steps():
    c = FakeClient(*[("tool_use", [tool_use(f"t{i}", "calculator", expression="1+1")]) for i in range(3)])
    assert run_agent("x", client=c, max_steps=3).stop == "max_steps"

def test_graph_multihop():
    g = tools.GRAPH
    facts = graphrag.neighborhood(g, ["Schema Registry"], hops=2)
    assert ("Carol Diaz", "leads", "Beacon") in facts
    assert any("Beacon" in c and "Carol Diaz" in c for c in graphrag.communities(g))
