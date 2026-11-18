"""`kata` - run YOUR implementations of the katas.   uv run kata --help
  kata list                      progress on all katas
  kata reset k01 [--from blank|starter|solution] [--force]    create/overwrite your mine.py
  kata test k01                  run the kata's tests against your mine.py (katas 1-4)
  kata live k05 [--runs 3]       run your mine.py against the real model (katas 5-6)
  kata diff k01                  your code vs the reference (look AFTER your attempt)
"""
import argparse, difflib, os, re, shutil, subprocess, sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
LAB = PKG.parents[1]
LIVE = {"k05", "k06"}

def resolve(arg: str) -> Path:
    m = re.fullmatch(r"k?0*(\d+)", arg.strip().lower())
    if not m: raise SystemExit(f"unknown kata {arg!r}; use k01..k06")
    hits = sorted(PKG.glob(f"k{int(m.group(1)):02d}_*"))
    if not hits: raise SystemExit(f"no such kata {arg!r}; use k01..k06")
    return hits[0]

def kid(d: Path) -> str: return d.name[:3]

def _source(d: Path, origin: str) -> Path:
    if origin == "blank" and (d / "skeleton.py").exists(): return d / "skeleton.py"
    if origin == "solution": return d / "solution.py"
    return d / "starter.py"          # katas 5-6 have no blank form: you edit the starter

def cmd_reset(a):
    d = resolve(a.kata); mine = d / "mine.py"
    if mine.exists() and not a.force: raise SystemExit(f"{mine.relative_to(LAB)} already exists (your work!). Use --force to overwrite.")
    src = _source(d, a.origin)
    shutil.copyfile(src, mine)
    note = " (peeking at the solution!)" if a.origin == "solution" else ""
    print(f"created {mine.relative_to(LAB)} from {src.name}{note}\nedit it, then: uv run kata {'live' if kid(d) in LIVE else 'test'} {kid(d)}")

def _need_mine(d: Path):
    if not (d / "mine.py").exists(): raise SystemExit(f"no mine.py yet: run `uv run kata reset {kid(d)}` first")

def _pytest(d: Path, quiet=False, extra=()):
    env = {**os.environ, "KATA_IMPL": "mine"}
    cmd = [sys.executable, "-m", "pytest", str(LAB / "tests" / f"test_{kid(d)}.py"), "-q", "--no-header", *extra]
    return subprocess.run(cmd, env=env, cwd=LAB, capture_output=quiet, text=True)

def cmd_test(a):
    d = resolve(a.kata)
    if kid(d) in LIVE: raise SystemExit(f"{kid(d)} needs the real model: use `uv run kata live {kid(d)}`")
    _need_mine(d); raise SystemExit(_pytest(d, extra=["-x"] if a.first else []).returncode)

def cmd_live(a):
    d = resolve(a.kata)
    if kid(d) not in LIVE: raise SystemExit(f"{kid(d)} is checked by tests: use `uv run kata test {kid(d)}`")
    _need_mine(d)
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_PROFILE")):
        print("note: neither ANTHROPIC_API_KEY nor ANTHROPIC_PROFILE is set (e.g. `export ANTHROPIC_PROFILE=dev`)", file=sys.stderr)
    from .live import main as live_main
    live_main([d.name, "--impl", "mine", "--runs", str(a.runs), *(["--verbose"] if a.verbose else [])])

def cmd_diff(a):
    d = resolve(a.kata); _need_mine(d)
    mine, ref = (d / "mine.py").read_text().splitlines(), (d / "solution.py").read_text().splitlines()
    out = list(difflib.unified_diff(mine, ref, "your mine.py", "reference solution.py", lineterm=""))
    print("\n".join(out) if out else "identical to the reference")

def cmd_list(a):
    print(f"{'kata':<24}{'your file':<14}status")
    for d in sorted(PKG.glob("k0*_*")):
        if not (d / "mine.py").exists(): print(f"{d.name:<24}{'-':<14}not started: uv run kata reset {kid(d)}"); continue
        if kid(d) in LIVE: print(f"{d.name:<24}{'mine.py':<14}live: uv run kata live {kid(d)}"); continue
        r = _pytest(d, quiet=True); last = (r.stdout.strip().splitlines() or ["?"])[-1]
        print(f"{d.name:<24}{'mine.py':<14}{'PASS' if r.returncode == 0 else 'FAIL'}  {last}")

def main(argv=None):
    p = argparse.ArgumentParser(prog="kata", description="Run your own implementations of the agent katas.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    r = sub.add_parser("reset"); r.add_argument("kata"); r.add_argument("--from", dest="origin", choices=["blank", "starter", "solution"], default="blank")
    r.add_argument("--force", action="store_true"); r.set_defaults(fn=cmd_reset)
    t = sub.add_parser("test"); t.add_argument("kata"); t.add_argument("-x", "--first", action="store_true", help="stop at first failure"); t.set_defaults(fn=cmd_test)
    l = sub.add_parser("live"); l.add_argument("kata"); l.add_argument("--runs", type=int, default=3); l.add_argument("--verbose", action="store_true"); l.set_defaults(fn=cmd_live)
    sub.add_parser("diff").set_defaults(fn=cmd_diff); sub.choices["diff"].add_argument("kata")
    a = p.parse_args(argv); a.fn(a)

if __name__ == "__main__":
    main()
