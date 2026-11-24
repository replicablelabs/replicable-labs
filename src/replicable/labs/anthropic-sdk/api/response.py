"""Values you get back from `client.messages.create`. All StrEnums: they compare equal to the API's plain strings."""

from enum import StrEnum


class StopReason(StrEnum):
    """`response.stop_reason`: why the model stopped generating.

    The request succeeded (HTTP 200) in every case; the stop reason tells you what
    to do next. Branch on it explicitly and report any value you don't handle.

    The stop reason also decides whether the turn is over and whether the agent
    loop sends another request:

    | Stop reason                     | Turn completed? | Loop again?                  |
    |---------------------------------|-----------------|------------------------------|
    | `tool_use`                      | yes             | yes, after running the tools |
    | `pause_turn`                    | yes             | yes, resend history as is    |
    | `max_tokens`                    | no (truncated)  | yes, retry with a bigger one |
    | `end_turn`                      | yes             | no, final answer             |
    | `stop_sequence`                 | yes             | depends on your design       |
    | `refusal`                       | no              | no, report it                |
    | `model_context_window_exceeded` | no              | no, shrink the history first |

    Reset `max_tokens` only where a turn completed and the loop continues. Never
    run a tool from a `max_tokens` response: its `tool_use` input may be cut off.
    """

    END_TURN = "end_turn"
    """The model finished its turn naturally. Show the answer and stop. It may also
    be a question for the user: if so, their reply is the next `user` message."""

    MAX_TOKENS = "max_tokens"
    """The response hit the `max_tokens` you set for response token limits and the
    model's token generation was interrupted."""

    STOP_SEQUENCE = "stop_sequence"
    """The model produced one of the `stop_sequences` you passed in the request.
    `response.stop_sequence` says which. Unused unless you set stop sequences."""

    TOOL_USE = "tool_use"
    """The model wants tools run. Execu te each `tool_use` block, then reply with a
    `user` message of matching `tool_result` blocks and call the API again."""

    PAUSE_TURN = "pause_turn"
    """The model paused a long turn that uses server-side tools (web search, code
    execution). Send the conversation back as it is to let it continue."""

    REFUSAL = "refusal"
    """The model declined for safety reasons. `response.stop_details` has the category
    and an explanation. Surface it to the user; retrying the same request won't help."""

    MODEL_CONTEXT_WINDOW_EXCEEDED = "model_context_window_exceeded"
    """The model ran out of context window (prompt plus output) before finishing.
    The history is too long: shorten, summarise or compact it before retrying."""


COMPLETED_TURN_REASONS = frozenset(
    {
        StopReason.END_TURN,
        StopReason.TOOL_USE,
        StopReason.PAUSE_TURN,
        StopReason.STOP_SEQUENCE,
    }
)
"""Stop reasons that complete a turn (see the table above). `max_tokens`, `refusal`
and `model_context_window_exceeded` do not: the turn is cut short or refused."""


class BlockType(StrEnum):
    """`block.type` for the content blocks in `response.content`.

    Only the ones this kata can meet; the SDK has more (server tool results, etc.).
    """

    TEXT = "text"
    THINKING = "thinking"
    REDACTED_THINKING = "redacted_thinking"
    TOOL_USE = "tool_use"
    SERVER_TOOL_USE = "server_tool_use"
