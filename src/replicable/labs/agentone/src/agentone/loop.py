"""THE core exercise: an agent from scratch on the raw Anthropic Messages API.

Know this file cold. The whole 'agent' idea is: call model -> if stop_reason == 'tool_use',
run every tool_use block, append ONE user message of tool_result blocks, repeat.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
import anthropic
from . import tools

MODEL = os.environ.get("AGENTONE_MODEL", "claude-sonnet-5-5")
SYSTEM = ("You answer questions about a company using the graph_search tool. "
          "Multi-hop questions need multiple searches. Cite facts; if unsure, say so.")

@dataclass
class Result:
    answer: str
    messages: list
    steps: int
    tool_calls: list[tuple[str, dict]] = field(default_factory=list)
    stop: str = "end_turn"

def run_agent(question: str, client: anthropic.Anthropic | None = None, max_steps: int = 8,
              system: str = SYSTEM, model: str = MODEL) -> Result:
    client = client or anthropic.Anthropic()  # honours ANTHROPIC_BASE_URL => proxy works unchanged
    messages: list[dict] = [{"role": "user", "content": question}]
    calls: list[tuple[str, dict]] = []
    for step in range(1, max_steps + 1):
        resp = client.messages.create(model=model, max_tokens=1024, system=system,
                                      tools=tools.schemas(), messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            return Result(text, messages, step, calls, resp.stop_reason)
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                calls.append((b.name, b.input))
                out, is_err = tools.run_tool(b.name, b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out, "is_error": is_err})
        messages.append({"role": "user", "content": results})
    return Result("(max_steps reached)", messages, max_steps, calls, "max_steps")

if __name__ == "__main__":
    import sys
    r = run_agent(" ".join(sys.argv[1:]) or "Who leads the team that owns the Schema Registry?")
    print(r.answer, f"\n[{r.steps} steps, tools={r.tool_calls}]")
