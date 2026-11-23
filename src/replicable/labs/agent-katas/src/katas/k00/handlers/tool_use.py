"""`tool_use`: the turn is complete and the model wants tools run."""

from ..api import request, response
from ..state import LoopState
from ..tools import run_tool


def on_tool_use(state: LoopState, resp) -> bool:
    """Run every requested tool, then queue the results for the next request.

    The assistant response is appended first, immediately followed by the user
    message holding the matching `tool_result` blocks. Returns False: loop again.
    """
    state.reset_max_tokens()

    tool_results = []
    for block in resp.content:
        if block.type != response.BlockType.TOOL_USE:
            continue
        state.metadata["tool_calls"].append({block.name: block.input})
        content, is_error = run_tool(block.name, block.input)
        tool_results.append(
            {
                "type": request.BlockType.TOOL_RESULT,
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            }
        )

    state.append_assistant(resp.content)
    state.append_user(tool_results)
    return False
