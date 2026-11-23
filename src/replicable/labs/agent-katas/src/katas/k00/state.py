"""The mutable state of one agent run, shared by the loop and the stop-reason handlers."""

from dataclasses import dataclass, field

from .api import request
from .utils import agent, utils


@dataclass
class AgentState:
    """Everything the agent loop reads and writes between turns.

    - `session`: the messages resent on every request (plain dicts only).
    - `max_tokens`: the cap for the next request.
    - `max_tokens_capped`: True after a bump, so the cap is reset once a turn completes.
    - `cutover_index`: position in `session` of the first truncated assistant message
      of an open "continue" run, or None when no run is open.
    - `metadata`: counters printed at the end of the run.
    - `result`: the final text answer, set by the `end_turn` handler.
    """

    session: list = field(default_factory=list)
    max_tokens: int = field(default_factory=utils.set_max_tokens_cap)
    max_tokens_capped: bool = False
    cutover_index: int | None = None
    metadata: dict = field(default_factory=lambda: {"turns": 0, "tool_calls": []})
    result: str = ""

    @classmethod
    def start(cls, prompt: str) -> "AgentState":
        """A fresh run whose only message is the user's prompt."""
        state = cls()
        state.append_user(prompt)
        return state

    def append_user(self, content) -> None:
        """Append a user message (a string or a list of blocks)."""
        self.session.append({"role": request.Role.USER, "content": content})

    def append_assistant(self, content) -> None:
        """Append a completed assistant response, as dicts.

        If a "continue" run is open, this response closes it: the run's fragments
        are merged with it into one assistant message, and the run is cleared.
        """
        self.session.append(
            {
                "role": request.Role.ASSISTANT,
                "content": utils.blocks_to_dicts(content),
            }
        )
        if self.cutover_index is not None:
            merged = agent.concatenate_interrupted_responses(
                self.session, self.cutover_index
            )
            self.session.append({"role": request.Role.ASSISTANT, "content": merged})
            self.cutover_index = None

    def bump_max_tokens(self) -> None:
        """Raise the cap so the same request can be resent with more room."""
        self.max_tokens = utils.increase_max_tokens_cap(self.max_tokens)
        self.max_tokens_capped = True

    def reset_max_tokens(self) -> None:
        """Return the cap to its starting value, if it was bumped."""
        if self.max_tokens_capped:
            self.max_tokens = utils.reset_max_tokens_cap()
            self.max_tokens_capped = False
