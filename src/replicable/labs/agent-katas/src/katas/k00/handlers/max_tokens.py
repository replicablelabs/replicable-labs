"""`max_tokens`: the response was cut off, so the turn did not complete."""

from ..api import request, response
from ..state import LoopState
from ..utils import utils

CUTOVER_MESSAGE = utils.get_max_tokens_cutover_prompt()


def on_max_tokens(state: LoopState, resp) -> bool:
    """Recover from a truncated response. Always returns False: loop again.

    - Any `tool_use` block: its input may be cut off and cannot be continued, so
      discard the response, raise the cap and resend the same request.
    - Text and no tools: keep only the text, append the "continue" message and
      remember where the run started. The fragments are merged when a later
      response completes the turn (see `LoopState.append_assistant`).
    - Nothing usable (e.g. only thinking): raise the cap and resend.
    """
    if any(block.type == response.BlockType.TOOL_USE for block in resp.content):
        state.bump_max_tokens()
        return False

    text_blocks = utils.blocks_to_dicts(
        [block for block in resp.content if block.type == response.BlockType.TEXT]
    )
    if not text_blocks:
        state.bump_max_tokens()
        return False

    if state.cutover_index is None:
        # first truncation of this run: remember where it starts
        state.cutover_index = len(state.session)
    state.session.append({"role": request.Role.ASSISTANT, "content": text_blocks})
    state.append_user(CUTOVER_MESSAGE)
    return False
