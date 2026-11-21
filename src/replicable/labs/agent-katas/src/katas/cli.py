"""`kata` - run the k00 sandbox.

    uv run kata run k00 "create a card about the capital of France"

Runs k00/agent.py's main(client, args) against the real model.
"""
import argparse
import os
import re
import sys

from .style import die, dim, pretty_tracebacks


def _client():
    """Build the Anthropic client, warning on stderr if no credentials are configured."""
    import anthropic

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_PROFILE")):
        print(
            "note: neither ANTHROPIC_API_KEY nor ANTHROPIC_PROFILE is set (e.g. `export ANTHROPIC_PROFILE=dev`)",
            file=sys.stderr,
        )
    return anthropic.Anthropic()


def cmd_run(a):
    """`kata run`: validate the kata name, then call `main(client, args)` in k00/agent.py."""
    if not re.fullmatch(r"k?0+", a.kata.strip().lower()):
        die(f"unknown kata {a.kata!r}; the only one is k00")
    from .k00 import agent

    if not hasattr(agent, "main"):
        die("k00/agent.py needs a `main(client, args)` function.")
    print(dim("[running k00/agent.py]"), flush=True)
    agent.main(_client(), a.args)


def main(argv=None):
    """Entry point for the `kata` command: parse `argv` and dispatch to the subcommand."""
    p = argparse.ArgumentParser(prog="kata", description="Run the k00 card-agent sandbox.")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run k00/agent.py against the real model")
    r.add_argument("kata", help="k00")
    r.add_argument("args", nargs="*", help="the prompt to send, e.g. a request about cards")
    r.set_defaults(fn=cmd_run)
    a = p.parse_args(argv)
    pretty_tracebacks()
    a.fn(a)


if __name__ == "__main__":
    main()
