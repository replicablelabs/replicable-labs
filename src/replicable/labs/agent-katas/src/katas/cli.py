"""`kata` - run the k00 sandbox.

    uv run kata run k00 "create a card about the capital of France"

Runs k00/mine.py's main(client, args) against the real model.
"""
import argparse
import os
import re
import sys

from .style import die, dim, pretty_tracebacks


def _client():
    import anthropic

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_PROFILE")):
        print(
            "note: neither ANTHROPIC_API_KEY nor ANTHROPIC_PROFILE is set (e.g. `export ANTHROPIC_PROFILE=dev`)",
            file=sys.stderr,
        )
    return anthropic.Anthropic()


def cmd_run(a):
    if not re.fullmatch(r"k?0+", a.kata.strip().lower()):
        die(f"unknown kata {a.kata!r}; the only one is k00")
    from .k00 import mine

    if not hasattr(mine, "main"):
        die("k00/mine.py needs a `main(client, args)` function.")
    print(dim("[running k00/mine.py]"), flush=True)
    mine.main(_client(), a.args)


def main(argv=None):
    p = argparse.ArgumentParser(prog="kata", description="Run the k00 card-agent sandbox.")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run k00/mine.py against the real model")
    r.add_argument("kata", help="k00")
    r.add_argument("args", nargs="*", help="the prompt to send, e.g. a request about cards")
    r.set_defaults(fn=cmd_run)
    a = p.parse_args(argv)
    pretty_tracebacks()
    a.fn(a)


if __name__ == "__main__":
    main()
