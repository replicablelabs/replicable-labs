"""Run the SAME question through three harnesses and compare answer / steps / tool calls.
  anthropic : loop.py        (raw Messages API, you own the loop)
  openai    : loop_openai.py (raw Chat Completions, you own the loop)
  deepagents: deep_agent.py  (framework owns the loop; model via DEEPAGENTS_MODEL, default Anthropic,
              e.g. DEEPAGENTS_MODEL=openai:gpt-4.1)
Usage: python -m agentone.harnesses [anthropic openai deepagents] -- "question" """
from __future__ import annotations
import os, sys, time
from types import SimpleNamespace as NS

def _anthropic(q):
    from .loop import run_agent; return run_agent(q)

def _openai(q):
    from .loop_openai import run_agent; return run_agent(q)

def _deepagents(q):
    from .deep_agent import build
    out = build(os.environ.get("DEEPAGENTS_MODEL", "anthropic:claude-sonnet-5-5")).invoke({"messages": [("user", q)]})
    msgs = out["messages"]
    calls = [(c["name"], c["args"]) for m in msgs for c in (getattr(m, "tool_calls", None) or [])]
    c = msgs[-1].content
    ans = c if isinstance(c, str) else "".join(b.get("text", "") for b in c if isinstance(b, dict))
    return NS(answer=ans, steps=sum(m.type == "ai" for m in msgs), tool_calls=calls)

HARNESSES = {"anthropic": _anthropic, "openai": _openai, "deepagents": _deepagents}

def compare(q: str, names=None) -> list[dict]:
    rows = []
    for n in names or HARNESSES:
        t = time.time()
        try: r = HARNESSES[n](q); rows.append(dict(harness=n, answer=r.answer, steps=r.steps,
                                                   tools=len(r.tool_calls), secs=round(time.time() - t, 1)))
        except Exception as e: rows.append(dict(harness=n, answer=f"ERROR {type(e).__name__}: {e}", steps=0, tools=0, secs=0))
    return rows

if __name__ == "__main__":
    a = sys.argv[1:]; names = [x for x in a[: a.index("--")]] if "--" in a else []
    q = " ".join(a[a.index("--") + 1:]) if "--" in a else "Who leads the team that owns the Schema Registry?"
    for r in compare(q, names or None): print(r)
