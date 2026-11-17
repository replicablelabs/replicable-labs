"""deepagents = LangGraph agent + planning (todos), virtual filesystem, subagents, summarisation, as middleware.
Learn what it adds over lg_agent.py: write_todos, ls/read_file/write_file/edit_file, task (subagent spawn)."""
from deepagents import create_deep_agent
from .lg_agent import graph_search, calculator

researcher = {
    "name": "graph-researcher",
    "description": "Chases multi-hop questions through the knowledge graph and returns a concise cited answer.",
    "system_prompt": "Use graph_search repeatedly until the chain of facts is complete. Return the answer plus the facts used.",
    "tools": [graph_search],
}

def build(model: str = "anthropic:claude-sonnet-5-5"):
    return create_deep_agent(
        model=model,
        tools=[graph_search, calculator],
        system_prompt="You are a lead analyst. Plan with write_todos, delegate graph questions to graph-researcher, then answer.",
        subagents=[researcher],
    )

if __name__ == "__main__":
    out = build().invoke({"messages": [("user", "Which team is on call if a dependency of the Ingestion Pipeline owned by another team fails?")]})
    print(out["messages"][-1].content)
