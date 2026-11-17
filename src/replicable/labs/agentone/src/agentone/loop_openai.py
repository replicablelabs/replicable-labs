"""Harness 1: the raw loop on OpenAI Chat Completions. Same shape as loop.py, different wire format:
assistant msg carries `tool_calls`; each result is its OWN {"role":"tool","tool_call_id":...} message;
tool args arrive as a JSON *string*; finish_reason == "tool_calls" is the continue signal."""
from __future__ import annotations
import json, os
from openai import OpenAI
from . import tools
from .loop import SYSTEM, Result

MODEL = os.environ.get("AGENTONE_OPENAI_MODEL", "gpt-4.1")

def _schemas() -> list[dict]:
    return [{"type": "function", "function": {"name": s["name"], "description": s["description"],
             "parameters": s["input_schema"]}} for s in tools.schemas()]

def run_agent(question: str, client: OpenAI | None = None, max_steps: int = 8,
              system: str = SYSTEM, model: str = MODEL) -> Result:
    client = client or OpenAI()  # honours OPENAI_BASE_URL => proxy / HF-compatible endpoints
    messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    calls: list[tuple[str, dict]] = []
    for step in range(1, max_steps + 1):
        resp = client.chat.completions.create(model=model, messages=messages, tools=_schemas())
        choice = resp.choices[0]; msg = choice.message
        messages.append(msg.model_dump(exclude_none=True) if hasattr(msg, "model_dump") else msg)
        if not msg.tool_calls:
            return Result(msg.content or "", messages, step, calls, choice.finish_reason)
        for tc in msg.tool_calls:
            try: args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError as e:
                out, err, args = f"bad JSON arguments: {e}", True, {}
            else:
                out, err = tools.run_tool(tc.function.name, args)
            calls.append((tc.function.name, args))
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": ("ERROR: " if err else "") + out})
    return Result("(max_steps reached)", messages, max_steps, calls, "max_steps")

if __name__ == "__main__":
    import sys
    r = run_agent(" ".join(sys.argv[1:]) or "Who leads the team that owns the Schema Registry?")
    print(r.answer, f"\n[{r.steps} steps, tools={r.tool_calls}]")
