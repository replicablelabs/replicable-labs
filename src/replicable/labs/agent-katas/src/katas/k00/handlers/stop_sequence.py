"""`stop_sequence`: the model produced one of the `stop_sequences` in the request."""

from ..state import AgentState
from ..utils.log import logger


def on_stop_sequence(state: AgentState, resp) -> bool:
    """Not handled yet. Returns False, which resends the identical request.

    TODO: decide what a stop sequence means for this agent. Nothing triggers it
    today (the request sets no `stop_sequences`).
    """
    logger.warning("stop_sequence is not handled")
    return False
