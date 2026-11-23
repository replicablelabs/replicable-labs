"""`kata` - run the card agent.

    uv run kata run "create a card about the capital of France"

Runs agent.py's main(client, args) against the real model.
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from style import die, dim, pretty_tracebacks

# Credentials: the lab's .env, if present. Exported shell variables take precedence.
load_dotenv(Path(__file__).resolve().parent / ".env", override=False)


def _client():
    """Build the Anthropic client, warning on stderr if no credentials are configured."""
    import anthropic

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_PROFILE")):
        print(
            "note: neither ANTHROPIC_API_KEY nor ANTHROPIC_PROFILE is set (e.g. `export ANTHROPIC_PROFILE=dev`)",
            file=sys.stderr,
        )
    return anthropic.Anthropic()


DEFAULT_PROMPT = "Hello, world?"


def cmd_run(a):
    """`kata run`: call `main(client, prompt)` in agent.py."""
    import agent
    import tracing

    if not hasattr(agent, "main"):
        die("agent.py needs a `main(client, prompt)` function.")
    print(dim("[running agent.py]"), flush=True)
    # The shell splits the prompt into words; rejoin them into one string.
    prompt = " ".join(a.args) or DEFAULT_PROMPT
    try:
        agent.main(_client(), prompt)
    finally:
        # Traces are sent in the background; wait so a short run doesn't drop them.
        tracing.flush()


def main(argv=None):
    """Entry point for the `kata` command: parse `argv` and dispatch to the subcommand."""
    p = argparse.ArgumentParser(prog="kata", description="Run the card-agent sandbox.")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run agent.py against the real model")
    r.add_argument("args", nargs="*", help="the prompt to send, e.g. a request about cards")
    r.set_defaults(fn=cmd_run)
    a = p.parse_args(argv)
    pretty_tracebacks()
    a.fn(a)


if __name__ == "__main__":
    main()
