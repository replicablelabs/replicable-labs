from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypedDict

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from openai_oauth import ChatGPTSession


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


def require_model_credentials() -> None:
    provider = os.environ.get("MODEL_PROVIDER", "openai")
    if provider not in {"openai", "anthropic"}:
        raise SystemExit("Choose openai or anthropic as the model provider.")
    if provider == "openai" and os.environ.get("OPENAI_AUTH_MODE") == "browser":
        if not ChatGPTSession(Path(os.environ.get("OPENAI_OAUTH_SESSION", "/run/openai-auth/session.json"))).connected():
            raise SystemExit("Sign in with ChatGPT through the lab launcher before starting browser mode.")
        return
    key_name = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    if not os.environ.get(key_name, "").strip():
        raise SystemExit(
            f"{key_name} is required for model calls. Restart with "
            "'replicable labs start deep-agents-langgraph-101' and enter your "
            "provider API key at the hidden prompt. LangSmith sign-in only authenticates tracing."
        )


def model_from_environment():
    require_model_credentials()
    provider = os.environ.get("MODEL_PROVIDER", "openai")
    model_name = os.environ.get("MODEL_NAME")
    if provider == "openai" and os.environ.get("OPENAI_AUTH_MODE") == "browser":
        from chatgpt_model import ChatGPTChatModel
        session = ChatGPTSession(Path(os.environ.get("OPENAI_OAUTH_SESSION", "/run/openai-auth/session.json")))
        if not model_name:
            raise SystemExit("Choose an available ChatGPT model through the lab launcher.")
        return ChatGPTChatModel(
            model=model_name, api_key=session.access_token,
            base_url="https://api.openai.com/v1", use_responses_api=True,
            streaming=True, store=False, use_previous_response_id=False,
            include=["reasoning.encrypted_content"], output_version="responses/v1",
            temperature=None, max_retries=0,
        )
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
            "between LangGraph workflow control, the Deep Agents harness, and "
            "LangSmith observability. Use the "
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


def configure_langsmith() -> None:
    # Tracing is part of the exercise; learners do not need to enable a flag.
    os.environ["LANGSMITH_TRACING"] = "true"
    # Empty Compose entries must not override endpoint/workspace/profile values
    # loaded by the SDK from a browser-login profile.
    for key in ("LANGSMITH_ENDPOINT", "LANGSMITH_WORKSPACE_ID", "LANGSMITH_PROFILE", "LANGSMITH_API_KEY"):
        if not os.environ.get(key, "").strip():
            os.environ.pop(key, None)
    if not os.environ.get("LANGSMITH_API_KEY"):
        path = Path(os.environ.get("LANGSMITH_CONFIG_FILE") or Path.home() / ".langsmith" / "config.json")
        try:
            data = json.loads(path.read_text())
            name = os.environ.get("LANGSMITH_PROFILE") or data.get("current_profile") or "default"
            profile = data.get("profiles", {}).get(name, {})
            oauth = profile.get("oauth") or {}
            authenticated = profile.get("api_key") or oauth.get("access_token") or oauth.get("refresh_token")
        except (OSError, ValueError, AttributeError, TypeError):
            authenticated = False
        if not authenticated:
            raise SystemExit("Sign in to LangSmith through the launcher: replicable labs start deep-agents-langgraph-101. It will offer browser sign-in and mount your login into the container.")
    if os.environ.get("LANGSMITH_AGENT_ID", "").strip():
        # Agent addressing must not be combined with legacy project settings.
        for key in ("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT", "LANGCHAIN_SESSION"):
            os.environ.pop(key, None)
    elif not os.environ.get("LANGSMITH_PROJECT", "").strip():
        os.environ["LANGSMITH_PROJECT"] = "replicable-deep-agents-langgraph-101"


def main() -> None:
    require_model_credentials()
    configure_langsmith()
    print("Replicable Lab: Deep Agents + LangGraph 101")
    print("Type 'exit' to stop. The outer workflow is LangGraph; the inner agent is Deep Agents.")
    print("LangSmith tracing is enabled. Open LangSmith to inspect each question's trace.")
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

