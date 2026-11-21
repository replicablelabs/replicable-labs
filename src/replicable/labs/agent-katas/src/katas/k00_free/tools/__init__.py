"""Tool registry: every card tool's definition, plus `run_tool` to execute one call.

Each tool is a sub-package whose `impl.py` holds one `@beta_tool` function named
like the tool. Its name, description and input schema all come from that
function's signature and docstring.
"""

import json

from ..utils.utils import ToolError
from . import create_card, delete_card, find_card, get_card, list_cards, schedule_card

_PACKAGES = [create_card, delete_card, find_card, get_card, list_cards, schedule_card]

# name -> decorated tool object (has .to_dict(), .call(), .func)
TOOLS = {pkg.__name__.rsplit(".", 1)[-1]: getattr(pkg.impl, pkg.__name__.rsplit(".", 1)[-1]) for pkg in _PACKAGES}

SCHEMAS = [tool.to_dict() for tool in TOOLS.values()]


def run_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run one tool call and return (content, is_error) for a tool_result block.

    Never raises: a bad call becomes an error result the model can read and retry.
    """
    tool = TOOLS.get(name)
    if tool is None:
        return f"Unknown tool {name!r}. Available: {', '.join(TOOLS)}.", True
    try:
        return tool.call(tool_input), False
    except ToolError as e:
        return str(e), True
    except (TypeError, ValueError) as e:
        return f"Invalid arguments for {name}: {e}", True
    except Exception as e:  # a crashing tool must not kill the loop
        return f"{name} failed: {type(e).__name__}: {e}", True
