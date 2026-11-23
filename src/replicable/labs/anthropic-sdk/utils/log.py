"""Debug logging.

Silent by default. Set the `DEBUG` environment variable to a truthy value
("1", "true", "yes", "on", any case) to see the `logger.debug(...)` output:

    DEBUG=True uv run kata run "your prompt"

Logs go to stderr, so the agent's own output on stdout stays clean.
"""

import logging
import os
import sys

_TRUTHY = {"1", "true", "yes", "on"}


def debug_enabled() -> bool:
    """True when the `DEBUG` environment variable is set to a truthy value."""
    return os.environ.get("DEBUG", "").strip().lower() in _TRUTHY


logger = logging.getLogger("anthropic-sdk")
logger.propagate = False
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.DEBUG if debug_enabled() else logging.WARNING)
