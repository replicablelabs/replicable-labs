"""The mutable state of one agent run, shared by the loop and the stop-reason handlers."""

import os
from dataclasses import dataclass, field
from enum import StrEnum

from .api import request
from .utils import agent, utils

STRATEGY_ENV_VAR = "K00_MAX_TOKENS_STRATEGY"


class MaxTokensStrategy(StrEnum):
    """How the agent recovers when a response is cut off by `max_tokens`."""

    RETRY = "retry"
    """Discard the truncated response, raise the cap, resend the same request.
    Exact and simple. The default."""

    CONTINUE = "continue"
    """For a text-only truncation, keep the text, send a "continue" message and
    stitch the fragments together afterwards ("stitching"). Cheaper on very long
    answers but unreliable: the model may restart, comment, or lose the seam.
    Kept behind this flag so it can be evaluated against `RETRY`."""


def _strategy_from_env() -> MaxTokensStrategy:
    """`K00_MAX_TOKENS_STRATEGY` (`retry` or `continue`); `retry` when unset."""
    return MaxTokensStrategy(os.environ.get(STRATEGY_ENV_VAR, "retry").strip().lower())


@dataclass
class AgentState:
    """Everything the agent loop reads and writes between turns.

    - `session`: the messages resent on every request (plain dicts only).
    - `max_tokens`: the cap for the next request.
    - `max_tokens_capped`: True after a bump, so the cap is reset once a turn completes.
    - `max_tokens_strategy`: how truncation is recovered. Defaults to the
      `K00_MAX_TOKENS_STRATEGY` environment variable, else `retry`; pass it to
      `start()` to choose per run (e.g. from an eval harness).
    - `cutover_index`: position in `session` of the first truncated assistant message
      of an open "continue" run, or None when no run is open. Only used by the
      `continue` strategy.
    - `metadata`: counters printed at the end of the run.
    - `result`: the final text answer, set by the `end_turn` handler.
    """

    session: list = field(default_factory=list)
    max_tokens: int = field(default_factory=utils.set_max_tokens_cap)
    max_tokens_capped: bool = False
    max_tokens_strategy: MaxTokensStrategy = field(default_factory=_strategy_from_env)
    cutover_index: int | None = None
    metadata: dict = field(default_factory=lambda: {"turns": 0, "tool_calls": []})
    result: str = ""

    @classmethod
    def start(cls, prompt: str, **fields) -> "AgentState":
        """A fresh run whose only message is the user's prompt.

        Extra keyword arguments set state fields, e.g.
        `AgentState.start(prompt, max_tokens_strategy=MaxTokensStrategy.CONTINUE)`.
        """
        state = cls(**fields)
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

    def bump_max_tokens(self) -> bool:
        """Raise the cap so the same request can be resent with more room.

        Returns False, changing nothing, when the cap is already at
        `MAX_TOKENS_CEILING`: the caller cannot retry bigger and must give up.
        """
        if self.max_tokens >= utils.MAX_TOKENS_CEILING:
            return False
        self.max_tokens = utils.increase_max_tokens_cap(self.max_tokens)
        self.max_tokens_capped = True
        return True

    def reset_max_tokens(self) -> None:
        """Return the cap to its starting value, if it was bumped."""
        if self.max_tokens_capped:
            self.max_tokens = utils.reset_max_tokens_cap()
            self.max_tokens_capped = False
