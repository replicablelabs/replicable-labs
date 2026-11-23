"""The card agent: the request sent to the model and the tool loop.

`uv run kata run "your prompt"` calls `main(client, args)` here. The loop only
calls the API and dispatches on `stop_reason`; what each stop reason means lives in
`handlers/`, and the state they share in `state.py`.
"""

from anthropic import Anthropic

from handlers import HANDLERS
from state import AgentState
from tools import SCHEMAS
from utils import utils
from utils.log import logger

MODEL = "claude-haiku-5-5"
SYSTEM = utils.get_system_prompt()
MAX_STEPS = 100


def main(client: Anthropic, args: list[str]) -> None:
    """run the agent"""
    prompt = " ".join(args) or "Hello, world?"
    state = AgentState.start(prompt)

    for _ in range(MAX_STEPS):
        state.metadata["turns"] += 1
        logger.debug("turn %d", state.metadata["turns"])
        resp = client.messages.create(
            model=MODEL,
            max_tokens=state.max_tokens,
            messages=state.session,
            system=SYSTEM,
            tools=SCHEMAS,
        )
        logger.debug(
            "    stop_reason=%s output_tokens=%d blocks=%s",
            resp.stop_reason,
            resp.usage.output_tokens,
            [block.type for block in resp.content],
        )

        handler = HANDLERS.get(resp.stop_reason)
        if handler(state, resp):
            break

    print(state.result)
    print(state.metadata)
