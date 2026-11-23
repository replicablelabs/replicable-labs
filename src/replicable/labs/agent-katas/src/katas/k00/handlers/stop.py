"""Stop reasons where resending the same request cannot succeed: report and stop."""

from ..state import LoopState
from ..utils.log import logger


def on_refusal(state: LoopState, resp) -> bool:
    """The model declined; retrying the same request would be refused again."""
    logger.error("refused: %s", resp.stop_details)
    return True


def on_context_window_exceeded(state: LoopState, resp) -> bool:
    """The history only grows, so a retry cannot succeed."""
    logger.error("context window exceeded")
    return True
