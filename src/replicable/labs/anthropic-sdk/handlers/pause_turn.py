"""`pause_turn`: the model paused a long turn that uses server-side tools."""

from state import AgentState
from utils.log import logger


def on_pause_turn(state: AgentState, resp) -> bool:
    """Not handled yet. Returns False, which resends the identical request.

    TODO: append the paused response to the session so the model can continue it;
    until then this would loop to `MAX_STEPS`. Nothing triggers it today (no
    server tools).
    """
    logger.warning("pause_turn is not handled")
    return False
