"""Stop reasons where resending the same request cannot succeed: report and stop."""

from state import AgentState
from utils.log import logger


def on_refusal(state: AgentState, resp) -> bool:
    """The model declined; retrying the same request would be refused again."""
    logger.error("refused: %s", resp.stop_details)
    return True


def on_context_window_exceeded(state: AgentState, resp) -> bool:
    """The history only grows, so a retry cannot succeed."""
    logger.error("context window exceeded")
    return True
