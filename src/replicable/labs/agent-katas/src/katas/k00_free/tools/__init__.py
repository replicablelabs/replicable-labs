"""Tool registry: every card tool's schema, plus `run_tool` to execute one call.

Each tool is a sub-package with `schema.py` (the dict sent to the API),
`description.md` (its text) and `impl.py` (a function named like the tool).
"""

import json

from ..utils.utils import ToolError
from . import create_card, delete_card, find_card, get_card, list_cards, schedule_card

TOOLS = [create_card, delete_card, find_card, get_card, list_cards, schedule_card]

SCHEMAS = [tool.schema.schema for tool in TOOLS]

_IMPLS = {
    tool.schema.schema["name"]: getattr(tool.impl, tool.schema.schema["name"])
    for tool in TOOLS
}


def run_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run one tool call and return (content, is_error) for a tool_result block.

    Never raises: a bad call becomes an error result the model can read and retry.
    """
    impl = _IMPLS.get(name)
    if impl is None:
        return f"Unknown tool {name!r}. Available: {', '.join(_IMPLS)}.", True
    try:
        return json.dumps(impl(**tool_input)), False
    except ToolError as e:
        return str(e), True
    except TypeError as e:
        return f"Invalid arguments for {name}: {e}", True
    except Exception as e:  # a crashing tool must not kill the loop
        return f"{name} failed: {type(e).__name__}: {e}", True
