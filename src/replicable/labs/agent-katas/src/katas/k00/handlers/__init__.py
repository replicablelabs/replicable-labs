"""One handler per `stop_reason`.

A handler is `(state, resp) -> bool`: it updates the `AgentState` for the next
request and returns True to stop the loop, False to send another request.
`HANDLERS` maps each stop reason to its handler; the loop dispatches through it.
"""

from collections.abc import Callable

from ..api.response import StopReason
from ..state import AgentState
from .end_turn import on_end_turn
from .max_tokens import on_max_tokens
from .pause_turn import on_pause_turn
from .stop import on_context_window_exceeded, on_refusal
from .stop_sequence import on_stop_sequence
from .tool_use import on_tool_use

Handler = Callable[[AgentState, object], bool]

HANDLERS: dict[str, Handler] = {
    StopReason.TOOL_USE: on_tool_use,
    StopReason.END_TURN: on_end_turn,
    StopReason.MAX_TOKENS: on_max_tokens,
    StopReason.REFUSAL: on_refusal,
    StopReason.MODEL_CONTEXT_WINDOW_EXCEEDED: on_context_window_exceeded,
    StopReason.PAUSE_TURN: on_pause_turn,
    StopReason.STOP_SEQUENCE: on_stop_sequence,
}
