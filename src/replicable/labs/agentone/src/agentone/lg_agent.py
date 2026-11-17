"""Same agent, hand-built in LangGraph. Learn: State, nodes, conditional edges, checkpointer, interrupts."""
from __future__ import annotations
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from . import tools as T
from .loop import MODEL, SYSTEM

@tool
def graph_search(query: str, hops: int = 2) -> str:
    """Search the company knowledge graph; returns facts 'A --rel--> B'. Call repeatedly for multi-hop."""
    return T.graph_search(query, hops)

@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression."""
    return T.calculator(expression)

TOOLS = [graph_search, calculator]

def build_graph(llm=None, checkpointer=None):
    llm = (llm or ChatAnthropic(model=MODEL)).bind_tools(TOOLS)

    def agent(state: MessagesState):                  # node: call the model
        return {"messages": [llm.invoke([("system", SYSTEM), *state["messages"]])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(TOOLS))              # node: run tool calls
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)  # tool_calls? -> "tools" else END
    g.add_edge("tools", "agent")                      # the loop
    return g.compile(checkpointer=checkpointer or MemorySaver())

if __name__ == "__main__":
    app = build_graph()
    out = app.invoke({"messages": [("user", "Who leads the team that owns the Schema Registry?")]},
                     {"configurable": {"thread_id": "t1"}})
    print(out["messages"][-1].content)
