"""`kata` - run YOUR implementations of the katas.   uv run kata --help
  kata list                      progress on all katas
  kata reset k01 [--from blank|starter|solution] [--force]    wipe your mine.py back to blank (it already exists)
  kata reset k01 --target starter [--force]                   restore the buggy starter.py to its original state
  kata test k01 [--all]          run the kata's tests against your mine.py (katas 1-4); stops at the first failure unless --all
                                 add --starter (the existing buggy code) or --solution (the reference) to run those instead
  kata live k05 [--runs 3]       run your mine.py against the real model (katas 5-6)
  kata run k01 [input...]        RUN the kata code (no tests) and print what happens step by step; see katas/run.py
  kata diff k01                  your code vs the reference (look AFTER your attempt)
"""
import argparse, difflib, os, re, shutil, subprocess, sys
from pathlib import Path

from .style import bold, cyan, dim, die, green, pretty_tracebacks, red

PKG = Path(__file__).resolve().parent
LAB = PKG.parents[1]
LIVE = {"k05", "k06"}

def resolve(arg: str) -> Path:
    m = re.fullmatch(r"k?0*(\d+)", arg.strip().lower())
    if not m: die(f"unknown kata {arg!r}; use k01..k06")
    hits = sorted(PKG.glob(f"k{int(m.group(1)):02d}_*"))
    if not hits: die(f"no such kata {arg!r}; use k01..k06")
    return hits[0]

def kid(d: Path) -> str: return d.name[:3]

def _blank_source(d: Path) -> Path: return d / "skeleton.py" if (d / "skeleton.py").exists() else d / "starter.py"

def _has_blank(d: Path) -> bool: return (d / "skeleton.py").exists() or (d / "starter.py").exists()

def _pristine(p: Path) -> str:
    """The COMMITTED text of a file (what it looked like before you edited it); falls back to the file itself outside git."""
    r = subprocess.run(["git", "show", f"HEAD:./{p.relative_to(LAB)}"], cwd=LAB, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else p.read_text()

def _hide_from_git():
    """mine.py and starter.py are committed pristine; tell git to ignore YOUR edits to them (local-only, idempotent, harmless outside git)."""
    files = [str(p.relative_to(LAB)) for name in ("mine.py", "starter.py") for p in PKG.glob(f"k0*_*/{name}") if _has_blank(p.parent)]
    if files: subprocess.run(["git", "update-index", "--skip-worktree", *files], cwd=LAB, capture_output=True)

def _source(d: Path, origin: str) -> Path:
    if origin == "blank" and (d / "skeleton.py").exists(): return d / "skeleton.py"
    if origin == "solution": return d / "solution.py"
    return d / "starter.py"          # katas 5-6 have no blank form: you edit the starter

def cmd_reset(a):
    d = resolve(a.kata)
    if a.target == "starter":      # restore the buggy starter.py to its committed state (after you fixed it and want to redo it)
        dest = d / "starter.py"
        if dest.read_text() != _pristine(dest) and not a.force:
            die(f"{dest.relative_to(LAB)} has your changes. Use --force to restore the original buggy version.")
        dest.write_text(_pristine(dest)); print(f"restored {dest.relative_to(LAB)} to the original buggy version"); return
    dest = d / "mine.py"
    src = _source(d, a.origin)
    text = src.read_text() if a.origin == "solution" else _pristine(src)
    if dest.exists() and dest.read_text() != _pristine(_blank_source(d)) and not a.force:
        die(f"{dest.relative_to(LAB)} has your changes. Use --force to wipe it back to blank.")
    dest.write_text(text)
    note = " (peeking at the solution!)" if a.origin == "solution" else ""
    print(f"wrote {dest.relative_to(LAB)} from {src.name}{note}\nedit it, then: uv run kata {'live' if kid(d) in LIVE else 'test'} {kid(d)}")

def _need_mine(d: Path):
    if not (d / "mine.py").exists(): die(f"{d.name}/mine.py is missing: run `uv run kata reset {kid(d)} --force` to recreate it")

def _pytest(d: Path, quiet=False, extra=(), impl="mine"):
    env = {**os.environ, "KATA_IMPL": impl}
    color = "no" if quiet else ("yes" if (sys.stdout.isatty() or os.environ.get("FORCE_COLOR")) and not os.environ.get("NO_COLOR") else "no")
    cmd = [sys.executable, "-m", "pytest", str(LAB / "tests" / f"test_{kid(d)}.py"), "-q", "--no-header", f"--color={color}", *extra]
    return subprocess.run(cmd, env=env, cwd=LAB, capture_output=quiet, text=True)

def cmd_test(a):
    d = resolve(a.kata)
    if kid(d) in LIVE: die(f"{kid(d)} needs the real model: use `uv run kata live {kid(d)}`")
    if a.impl == "mine": _need_mine(d)
    print(dim(f"[running {d.name}/{a.impl}.py]"), flush=True)
    raise SystemExit(_pytest(d, extra=[] if a.all else ["-x"], impl=a.impl).returncode)

def cmd_live(a):
    d = resolve(a.kata)
    if kid(d) not in LIVE: die(f"{kid(d)} is checked by tests: use `uv run kata test {kid(d)}`")
    if a.impl == "mine": _need_mine(d)
    print(dim(f"[running {d.name}/{a.impl}.py]"), flush=True)
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_PROFILE")):
        print("note: neither ANTHROPIC_API_KEY nor ANTHROPIC_PROFILE is set (e.g. `export ANTHROPIC_PROFILE=dev`)", file=sys.stderr)
    from .live import main as live_main
    live_main([d.name, "--impl", a.impl, "--runs", str(a.runs), *(["--verbose"] if a.verbose else [])])

def cmd_run(a):
    d = resolve(a.kata)
    if a.impl == "mine": _need_mine(d)
    print(dim(f"[running {d.name}/{a.impl}.py]"), flush=True)
    from .run import run
    run(d.name, a.impl, a.args)

def cmd_diff(a):
    d = resolve(a.kata); _need_mine(d)
    mine, ref = (d / "mine.py").read_text().splitlines(), (d / "solution.py").read_text().splitlines()
    out = list(difflib.unified_diff(mine, ref, "your mine.py", "reference solution.py", lineterm=""))
    print("\n".join(out) if out else "identical to the reference")

def cmd_list(a):
    print(f"{'kata':<24}{'your file':<14}status")
    for d in sorted(PKG.glob("k0*_*")):
        if not _has_blank(d): continue      # freestyle dirs (k00_free) have no skeleton/starter to compare against
        mine = d / "mine.py"
        if not mine.exists() or mine.read_text() == _pristine(_blank_source(d)):
            print(f"{d.name:<24}{'blank':<14}" + dim(f"not started: edit {mine.relative_to(LAB)}")); continue
        if kid(d) in LIVE: print(f"{d.name:<24}{'mine.py':<14}live: uv run kata live {kid(d)}"); continue
        r = _pytest(d, quiet=True); last = (r.stdout.strip().splitlines() or ["?"])[-1]
        print(f"{d.name:<24}{'mine.py':<14}" + (green("PASS") if r.returncode == 0 else red("FAIL")) + f"  {last}")

def main(argv=None):
    p = argparse.ArgumentParser(prog="kata", description="Run your own implementations of the agent katas.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    r = sub.add_parser("reset"); r.add_argument("kata"); r.add_argument("--from", dest="origin", choices=["blank", "starter", "solution"], default="blank")
    r.add_argument("--target", choices=["mine", "starter"], default="mine", help="which of your files to wipe (default: mine.py; starter = restore the buggy starter.py)")
    r.add_argument("--force", action="store_true"); r.set_defaults(fn=cmd_reset)
    def impl_flags(sp):
        g = sp.add_mutually_exclusive_group()
        g.add_argument("--mine", dest="impl", action="store_const", const="mine", help="run your mine.py (default)")
        g.add_argument("--starter", dest="impl", action="store_const", const="starter", help="run the existing buggy starter.py")
        g.add_argument("--solution", dest="impl", action="store_const", const="solution", help="run the reference solution.py")
        sp.set_defaults(impl="mine")
    t = sub.add_parser("test"); t.add_argument("kata"); impl_flags(t); t.add_argument("-a", "--all", action="store_true", help="show every failing test (default: stop at the first one)"); t.set_defaults(fn=cmd_test)
    l = sub.add_parser("live"); l.add_argument("kata"); impl_flags(l); l.add_argument("--runs", type=int, default=3); l.add_argument("--verbose", action="store_true"); l.set_defaults(fn=cmd_live)
    u = sub.add_parser("run"); u.add_argument("kata"); u.add_argument("args", nargs="*", help="kata-specific input, e.g. a question or an order id"); impl_flags(u); u.set_defaults(fn=cmd_run)
    sub.add_parser("diff").set_defaults(fn=cmd_diff); sub.choices["diff"].add_argument("kata")
    a = p.parse_args(argv); pretty_tracebacks(); _hide_from_git(); a.fn(a)

if __name__ == "__main__":
    main()
