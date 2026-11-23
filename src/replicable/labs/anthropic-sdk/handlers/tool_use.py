"""`tool_use`: the turn is complete and the model wants tools run."""

from api import request, response
from state import AgentState
from tools import run_tool
from utils.log import logger


def on_tool_use(state: AgentState, resp) -> bool:
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
        logger.debug(
            "    tool_use: %s(%s) -> is_error=%s", block.name, block.input, is_error
        )
        tool_results.append(
            {
                "type": request.BlockType.TOOL_RESULT,
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            }
        )

    if state.cutover_index is not None:
        logger.debug(
            "    tool_use: closes continue run from index %d", state.cutover_index
        )
    state.append_assistant(resp.content)
    state.append_user(tool_results)
    logger.debug("    tool_use: ran %d tool(s), sending results", len(tool_results))
    return False
