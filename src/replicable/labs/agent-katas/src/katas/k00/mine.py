import typing

from anthropic import Anthropic

from .tools import SCHEMAS
from .utils import utils

MODEL = "claude-haiku-5-5"
SYSTEM = utils.get_system_prompt()


def main(client: Anthropic, args: list[str]) -> None:
    """Freestyle entry point: `uv run kata run k00 "your prompt"`."""
    prompt = " ".join(args) or "Say hello in five words."

    resp = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        tools=SCHEMAS,
    )
    print(type(resp))
    utils.show(resp)
