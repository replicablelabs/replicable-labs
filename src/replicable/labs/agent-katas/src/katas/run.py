"""`kata run kNN [args]` - actually RUN a kata's code (no tests) and print what happens, step by step.
k01  run your agent loop against the real model with the shop tools     kata run k01 "Where is order 1002?"
k02  call lookup_order and show exactly what the model would read      kata run k02 1005
k03  call issue_refund and show the result + refunds recorded          kata run k03 1001 10
k04  classify a ticket with the real model (Haiku: only model that accepts forced tool_choice)   kata run k04 "I was charged twice"
k05  run an agent with YOUR tool descriptions (real model)             kata run k05 "What is your return policy?"
k06  run an agent with YOUR system prompt (real model, permissive refund tool)   kata run k06 "Refund order 1002"
Add --starter / --solution to run those files instead of mine.py."""
import json, os, sys
from .loader import load
from .style import bold, cyan, dim, die, green, red, yellow
from .world import World

def _clip(x, n=220):
    x = str(x).replace("\n", " ")
    return x if len(x) <= n else x[:n] + f"... [{len(x)} chars]"

def _client():
    import anthropic
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_PROFILE")):
        print("note: neither ANTHROPIC_API_KEY nor ANTHROPIC_PROFILE is set (e.g. `export ANTHROPIC_PROFILE=dev`)", file=sys.stderr)
    return anthropic.Anthropic()

def _traced(impls):
    """Wrap tool callables so every call and result is printed as it happens."""
    def wrap(name, fn):
        def f(**args):
            print(cyan(f"  -> {name}({_clip(json.dumps(args), 120)})"), flush=True)
            try: out = fn(**args)
            except Exception as e: print(red(f"  <- ERROR {type(e).__name__}: {_clip(e)}"), flush=True); raise
            print(green(f"  <- {_clip(out)}"), flush=True); return out
        return f
    return {n: wrap(n, fn) for n, fn in impls.items()}

def _agent_run(run_agent, question, schemas, system, enforce=True):
    from .world_tools import impls
    world = World()
    print(f"question: {question}\n", flush=True)
    try:
        r = run_agent(question, _client(), schemas, _traced(impls(world, enforce)), system=system, max_steps=8)
    except NotImplementedError:
        die("your run_agent is not implemented yet (it still raises NotImplementedError).")
    print(f"\n{bold('ANSWER:')} {r.answer}\n" + dim(f"(steps={r.steps}, stop={r.stop})"))
    if world.refunds: print(f"refunds recorded: {world.refunds}")

SHOP_SYSTEM = "You are a customer-support agent for an online shop. Use the tools to help the customer."

def run(kata_dir: str, impl: str, args: list[str]):
    k = kata_dir[:3]; m = load(kata_dir, impl)
    if k == "k01":
        from .k05_descriptions.solution import SCHEMAS
        _agent_run(m.run_agent, " ".join(args) or "Where is order 1002, and what did it contain?", SCHEMAS, SHOP_SYSTEM)
    elif k == "k02":
        oid = args[0] if args else "1005"
        try: out = m.lookup_order(World(), oid)
        except NotImplementedError: die("your lookup_order is not implemented yet.")
        print(f"lookup_order(order_id={oid!r}) returned {len(out)} characters:\n\n{out}")
    elif k == "k03":
        oid, amount = (args + ["1001", "10"])[:2]
        w = World()
        try: content, err = m.issue_refund(w, oid, float(amount), "demo")
        except NotImplementedError: die("your issue_refund is not implemented yet.")
        except KeyError as e: die(f"your issue_refund raised KeyError({e}): it crashed instead of returning an error for the model.")
        print(f"issue_refund({oid!r}, {amount}) -> is_error={err}\n{content}\nrefunds recorded: {w.refunds or 'none'}")
    elif k == "k04":
        text = " ".join(args) or "I was charged twice for my order and I need this fixed today."
        model = os.environ.get("KATA_K04_MODEL", "claude-haiku-5-5")   # forced tool_choice is rejected by Sonnet/Opus/Fable 5.x
        print(f"(model: {model}; forced tool_choice is only accepted by some models)")
        try: print(f"ticket: {text}\n-> {m.classify_ticket(_client(), text, model=model)}")
        except NotImplementedError: die("your classify_ticket is not implemented yet.")
    elif k == "k05":
        from .k01_loop.solution import run_agent
        _agent_run(run_agent, " ".join(args) or "Where is order #1002?", m.SCHEMAS, m.SYSTEM)
    elif k == "k06":
        from .k01_loop.solution import run_agent
        _agent_run(run_agent, " ".join(args) or "Order 1005 arrived with the wrong items. Please refund me $200.", m.SCHEMAS, m.SYSTEM, enforce=False)
