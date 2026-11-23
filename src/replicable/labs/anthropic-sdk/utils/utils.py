from pathlib import Path

from rich.pretty import pprint

from .log import logger

MAX_TOKENS_CEILING = 128_000
"""The model's maximum output tokens (`claude-haiku-5-5`). A larger `max_tokens`
cannot be requested, so retrying bigger stops being possible at this value."""


class ToolError(Exception):
    """Raised by a tool for bad arguments; the loop turns it into an is_error tool_result."""


def show(resp, keep_none: bool = False) -> None:
    """Pretty-print a Message as a plain dict. None fields are dropped unless keep_none=True."""
    pprint(resp.model_dump(exclude_none=not keep_none), expand_all=True)


def blocks_to_dicts(blocks) -> list[dict]:
    """Convert content blocks to plain dicts, ready to store in the session.

    SDK blocks (from `resp.content`) are Pydantic models, so they are dumped with
    `None` fields dropped. Anything that is already a dict is passed through
    unchanged, so the function is safe to call on a mix of both. Returns a new
    list; filtering (e.g. text only) is the caller's job.
    """
    return [
        block if isinstance(block, dict) else block.model_dump(exclude_none=True)
        for block in blocks
    ]


def get_system_prompt():
    """Read the system prompt from `prompts/system.md`, stripped of surrounding whitespace."""
    return (
        (Path(__file__).parent.parent / "prompts" / "system.md")
        .read_text(encoding="utf-8")
        .strip()
    )


def get_max_tokens_cutover_prompt():
    """Read the "continue" prompt from `prompts/max_tokens_merge.md`, stripped of surrounding whitespace."""
    return (
        (Path(__file__).parent.parent / "prompts" / "max_tokens_merge.md")
        .read_text(encoding="utf-8")
        .strip()
    )


def set_max_tokens_cap():
    """Return the starting `max_tokens` for a request.

    Deliberately tiny (100) so a `max_tokens` stop is easy to trigger while
    practising the recovery paths in the agent loop. Raise it for real use.
    """
    return 100


def reset_max_tokens_cap():
    """Return `max_tokens` to its starting value after a turn completes.

    Call it where a turn finished and the loop continues (e.g. after running
    tools), so a bump made to survive one truncation does not stick for the rest
    of the session. Currently just `set_max_tokens_cap()`.
    """
    logger.debug("reset tokens cap")
    return set_max_tokens_cap()


def increase_max_tokens_cap(max_tokens):
    """Return a larger `max_tokens`, for retrying a request that was truncated.

    Used when a `max_tokens` response had nothing worth keeping (e.g. only
    `tool_use` blocks, whose inputs may be cut off), so the same request is resent
    with more room. Doubles `max_tokens`, clamped to `MAX_TOKENS_CEILING`. Callers
    must check for the ceiling themselves: at the ceiling this returns the same
    value, and resending would truncate again.
    """
    bigger = min(max_tokens * 2, MAX_TOKENS_CEILING)
    logger.debug("increased tokens cap to %d", bigger)
    return bigger
