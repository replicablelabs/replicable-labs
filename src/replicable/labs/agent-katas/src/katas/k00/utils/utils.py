from pathlib import Path

from rich.pretty import pprint


class ToolError(Exception):
    """Raised by a tool for bad arguments; the loop turns it into an is_error tool_result."""


def show(resp, keep_none: bool = False) -> None:
    """Pretty-print a Message as a plain dict. None fields are dropped unless keep_none=True."""
    pprint(resp.model_dump(exclude_none=not keep_none), expand_all=True)


def get_system_prompt():
    """Read the system prompt from `k00/prompts/system.md`, stripped of surrounding whitespace."""
    return (
        (Path(__file__).parent.parent / "prompts" / "system.md")
        .read_text(encoding="utf-8")
        .strip()
    )
