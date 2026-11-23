"""`end_turn`: the model finished; its text is the final answer."""

from ..api import response
from ..state import LoopState


def on_end_turn(state: LoopState, resp) -> bool:
    """Store the response (merging any open "continue" run) and take its text as
    the result. Returns True: stop the loop.
    """
    state.append_assistant(resp.content)
    state.result = "".join(
        block["text"]
        for block in state.session[-1]["content"]
        if block["type"] == response.BlockType.TEXT
    )
    return True
