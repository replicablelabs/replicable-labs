from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph


class LabState(TypedDict, total=False):
    question: str
    context: str
    answer: str


def read_notes() -> str:
    notes_dir = Path("/app/notes")
    return "\n\n".join(path.read_text() for path in sorted(notes_dir.glob("*.md")))


@tool
def explain_concept(concept: str) -> str:
    """Return a short explanation of a concept named in the local lab notes."""
    notes = read_notes()
    lowered = concept.lower()
    matching = [paragraph for paragraph in notes.split("\n\n") if lowered in paragraph.lower()]
    return "\n\n".join(matching) or f"No local note matched '{concept}'. Explain it from first principles."


def model_from_environment():
    provider = os.environ.get("MODEL_PROVIDER", "openai")
    model_name = os.environ.get("MODEL_NAME")
    if not model_name:
        model_name = "gpt-4.1-mini" if provider == "openai" else "claude-3-5-haiku-latest"
    return init_chat_model(model_name, model_provider=provider, temperature=0)


def prepare(state: LabState) -> LabState:
    return {"context": read_notes()}


def run_deep_agent(state: LabState) -> LabState:
    agent = create_deep_agent(
        model=model_from_environment(),
        tools=[explain_concept],
        system_prompt=(
            "You are a patient teacher. Help the learner understand the difference "
            "between LangGraph workflow control and the Deep Agents harness. Use the "
            "local notes tool when useful. Always name which layer you are describing."
        ),
    )
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Local context:\n{state['context']}\n\n"
                        f"Learner question: {state['question']}"
                    ),
                }
            ]
        }
    )
    message = result["messages"][-1]
    return {"answer": message.content if isinstance(message.content, str) else str(message.content)}


def build_graph():
    graph = StateGraph(LabState)
    graph.add_node("prepare", prepare)
    graph.add_node("deep_agent", run_deep_agent)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "deep_agent")
    graph.add_edge("deep_agent", END)
    return graph.compile()


def main() -> None:
    print("Replicable Lab: Deep Agents + LangGraph 101")
    print("Type 'exit' to stop. The outer workflow is LangGraph; the inner agent is Deep Agents.")
    workflow = build_graph()
    while True:
        try:
            question = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        result = workflow.invoke({"question": question})
        print(f"\nAgent> {result['answer']}")


if __name__ == "__main__":
    main()

