"""Tool registry: every card tool's definition, plus `run_tool` to execute one call.

Each tool is a module named like the tool (`get_card.py`) holding one `@tool`
function with the same name. Its name, description and input schema all come
from that function's signature and docstring.
"""

from ..utils.utils import ToolError
from .create_card import create_card
from .delete_card import delete_card
from .find_card import find_card
from .get_card import get_card
from .list_cards import list_cards
from .schedule_card import schedule_card

# name -> decorated tool object (has .to_dict(), .call(), .func)
TOOLS = {
    "create_card": create_card,
    "delete_card": delete_card,
    "find_card": find_card,
    "get_card": get_card,
    "list_cards": list_cards,
    "schedule_card": schedule_card,
}

SCHEMAS = [tool.to_dict() for tool in TOOLS.values()]


def run_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Execute one tool call requested by the model.

    Looks `name` up in `TOOLS` and calls it with `tool_input` (the `tool_use`
    block's `input` dict).

    Returns a `(content, is_error)` pair that maps onto a `tool_result` block:
    - `content`: the tool's JSON output on success, or a plain-text error message
      on failure.
    - `is_error`: `True` when the call failed, so the model knows not to treat
      `content` as a real result.

    Never raises. Each of these becomes an error result the model can read and
    retry: an unknown tool name, a `ToolError` raised by the tool, bad arguments
    (`TypeError` / `ValueError`), and any other exception the tool throws.
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
