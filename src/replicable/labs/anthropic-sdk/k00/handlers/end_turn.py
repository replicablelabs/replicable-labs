"""`end_turn`: the model finished; its text is the final answer."""

from ..api import response
from ..state import AgentState
from ..utils.log import logger


def on_end_turn(state: AgentState, resp) -> bool:
    """Store the response (merging any open "continue" run) and take its text as
    the result. Returns True: stop the loop.
    """
    if state.cutover_index is not None:
        logger.debug(
            "    end_turn: closes continue run from index %d", state.cutover_index
        )
    state.append_assistant(resp.content)
    state.result = "".join(
        block["text"]
        for block in state.session[-1]["content"]
        if block["type"] == response.BlockType.TEXT
    )
    logger.debug("    end_turn: final answer, %d chars", len(state.result))
    return True
