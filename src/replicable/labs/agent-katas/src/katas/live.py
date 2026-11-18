"""Run the live katas against the real Anthropic API:
    uv run python -m katas.live k05_descriptions [--impl solution] [--runs 3] [--verbose]
Uses the reference loop (kata 1 solution) and reference tool implementations, so only YOUR schemas / system prompt vary."""
import argparse, os
from . import cases as C
from .k01_loop.solution import run_agent
from .loader import load
from .world import World
from .world_tools import impls as make_impls

def run_case(case, schemas, system, client, model=None, enforce_refund_rules=True) -> C.Trajectory:
    world, calls, errors = World(), [], [0]
    base = make_impls(world, enforce_refund_rules)
    if case.setup: case.setup(world)
    def rec(name):
        def f(**a):
            calls.append((name, a))
            try: return base[name](**a)
            except Exception: errors[0] += 1; raise
        return f
    res = run_agent(case.user, client, schemas, {n: rec(n) for n in base}, system=system, max_steps=8, **({"model": model} if model else {}))
    return C.Trajectory(calls, res.answer, res.stop, world, errors[0])

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("kata", choices=["k05_descriptions", "k06_system_prompt"])
    ap.add_argument("--impl", default=None); ap.add_argument("--runs", type=int, default=3); ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    import anthropic
    client, mod = anthropic.Anthropic(), load(a.kata, a.impl)
    cases = C.K05 if a.kata == "k05_descriptions" else C.K06
    total = passed = 0
    for case in cases:
        ok_n, reasons = 0, []
        for _ in range(a.runs):
            t = run_case(case, mod.SCHEMAS, mod.SYSTEM, client, enforce_refund_rules=a.kata != "k06_system_prompt")
            ok, why = case.grade(t); ok_n += ok; total += 1; passed += ok
            if not ok: reasons.append(why)
            if a.verbose: print(f"   [{case.name}] calls={t.calls} final={t.final[:140]!r}")
        print(f"{'PASS' if ok_n == a.runs else 'FAIL'}  {case.name:<18} {ok_n}/{a.runs}" + (f"   e.g. {reasons[0]}" if reasons else ""))
    print(f"\n{passed}/{total} runs passed  ({a.kata}, impl={a.impl or os.environ.get('KATA_IMPL', 'starter')})")

if __name__ == "__main__":
    main()
