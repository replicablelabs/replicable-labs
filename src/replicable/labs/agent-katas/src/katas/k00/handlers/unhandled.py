"""Stop reasons this kata does not handle yet.

Both just loop again without changing anything, which resends the identical
request until `MAX_STEPS`. Nothing here triggers them (no server tools, no stop
sequences), but they are the next runaway risk if that changes.
"""

from ..state import LoopState
from ..utils.log import logger


def on_pause_turn(state: LoopState, resp) -> bool:
    """TODO: append the paused response so the model can continue it."""
    logger.warning("pause_turn is not handled")
    return False


def on_stop_sequence(state: LoopState, resp) -> bool:
    """TODO: decide what a stop sequence means for this agent."""
    logger.warning("stop_sequence is not handled")
    return False
