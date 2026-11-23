"""`max_tokens`: the response was cut off, so the turn did not complete."""

from ..api import request, response
from ..state import AgentState, MaxTokensStrategy
from ..utils import utils
from ..utils.log import logger

CUTOVER_MESSAGE = utils.get_max_tokens_cutover_prompt()


def on_max_tokens(state: AgentState, resp) -> bool:
    """Recover from a truncated response. Returns True only when it cannot.

    The default strategy (`retry`) always discards the truncated response, raises
    the cap and resends the same request. Under the `continue` strategy a
    text-only truncation is stitched instead (see `_continue`); everything else
    still retries:

    - Any `tool_use` block: its input may be cut off and cannot be continued.
    - Nothing usable (e.g. only thinking): there is nothing to keep.
    """
    if any(block.type == response.BlockType.TOOL_USE for block in resp.content):
        logger.debug("    max_tokens: has tool_use -> discard response, retry bigger")
        return _retry_bigger(state)

    text_blocks = utils.blocks_to_dicts(
        [block for block in resp.content if block.type == response.BlockType.TEXT]
    )
    if not text_blocks:
        logger.debug("    max_tokens: no text kept -> discard response, retry bigger")
        return _retry_bigger(state)

    if state.max_tokens_strategy is not MaxTokensStrategy.CONTINUE:
        logger.debug("    max_tokens: strategy=retry -> discard response, retry bigger")
        return _retry_bigger(state)

    return _continue(state, text_blocks)


def _retry_bigger(state: AgentState) -> bool:
    """Raise the cap for the next (identical) request. True: already at the ceiling."""
    if state.bump_max_tokens():
        return False
    logger.error(
        "max_tokens ceiling reached (%d): the response still does not fit",
        state.max_tokens,
    )
    return True


def _continue(state: AgentState, text_blocks: list[dict]) -> bool:
    """Stitching: keep the text, append the "continue" message, merge later.

    The index where the run started is remembered; the fragments are merged when a
    later response completes the turn (see `AgentState.append_assistant`).
    """
    if state.cutover_index is None:
        # first truncation of this run: remember where it starts
        state.cutover_index = len(state.session)
        logger.debug("    max_tokens: new continue run at index %d", state.cutover_index)
    else:
        logger.debug("    max_tokens: run from index %d continues", state.cutover_index)
    logger.debug(
        "    max_tokens: kept %d text block(s), tail %r -> sending continue",
        len(text_blocks),
        text_blocks[-1]["text"][-30:],
    )
    state.session.append({"role": request.Role.ASSISTANT, "content": text_blocks})
    state.append_user(CUTOVER_MESSAGE)
    return False
