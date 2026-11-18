"""KATA 1 reference loop (also used by the live katas)."""
import os
from dataclasses import dataclass

MODEL = os.environ.get("KATA_MODEL", "claude-sonnet-5-5")

@dataclass
class Result:
    answer: str
    steps: int
    stop: str

def _run_tool(impls, name, args):
    """Never raise into the loop: unknown tools and exceptions go back to the model as is_error results."""
    if name not in impls: return f"Unknown tool {name!r}. Available tools: {sorted(impls)}", True
    try: return str(impls[name](**args)), False
    except Exception as e: return f"{type(e).__name__}: {e}", True

def run_agent(question, client, schemas, impls, system="", max_steps=8, model=MODEL) -> Result:
    messages = [{"role": "user", "content": question}]
    for step in range(1, max_steps + 1):
        resp = client.messages.create(model=model, max_tokens=1024, system=system, tools=schemas, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})           # verbatim, incl. tool_use blocks
        if resp.stop_reason != "tool_use":
            return Result("".join(b.text for b in resp.content if b.type == "text"), step, resp.stop_reason)
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                content, is_err = _run_tool(impls, b.name, b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": content, "is_error": is_err})
        messages.append({"role": "user", "content": results})                      # ONE message, all results
    return Result("(stopped: max_steps reached)", max_steps, "max_steps")
