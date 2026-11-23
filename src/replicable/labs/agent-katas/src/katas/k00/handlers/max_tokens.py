"""`max_tokens`: the response was cut off, so the turn did not complete."""

from ..api import request, response
from ..state import AgentState
from ..utils import utils
from ..utils.log import logger

CUTOVER_MESSAGE = utils.get_max_tokens_cutover_prompt()


def on_max_tokens(state: AgentState, resp) -> bool:
    """Recover from a truncated response. Always returns False: loop again.

    - Any `tool_use` block: its input may be cut off and cannot be continued, so
      discard the response, raise the cap and resend the same request.
    - Text and no tools: keep only the text, append the "continue" message and
      remember where the run started. The fragments are merged when a later
      response completes the turn (see `AgentState.append_assistant`).
    - Nothing usable (e.g. only thinking): raise the cap and resend.
    """
    if any(block.type == response.BlockType.TOOL_USE for block in resp.content):
        logger.debug("    max_tokens: has tool_use -> discard response, retry bigger")
        state.bump_max_tokens()
        return False

    text_blocks = utils.blocks_to_dicts(
        [block for block in resp.content if block.type == response.BlockType.TEXT]
    )
    if not text_blocks:
        logger.debug("    max_tokens: no text kept -> discard response, retry bigger")
        state.bump_max_tokens()
        return False

    if state.cutover_index is None:
        # first truncation of this run: remember where it starts
        state.cutover_index = len(state.session)
        logger.debug("    max_tokens: new continue run at index %d", state.cutover_index)
    else:
        logger.debug(
            "    max_tokens: run from index %d continues", state.cutover_index
        )
    logger.debug(
        "    max_tokens: kept %d text block(s), tail %r -> sending continue",
        len(text_blocks),
        text_blocks[-1]["text"][-30:],
    )
    state.session.append({"role": request.Role.ASSISTANT, "content": text_blocks})
    state.append_user(CUTOVER_MESSAGE)
    return False
