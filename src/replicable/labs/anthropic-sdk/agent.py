"""The card agent: the request sent to the model and the tool loop.

`uv run kata run "your prompt"` calls `main(client, prompt)` here. The loop only
calls the API and dispatches on `stop_reason`; what each stop reason means lives in
`handlers/`, and the state they share in `state.py`.
"""

import tracing
from anthropic import Anthropic
from handlers import HANDLERS
from langsmith import traceable
from langsmith.run_helpers import set_run_metadata
from state import AgentState
from tools import SCHEMAS
from utils import utils
from utils.log import logger

MODEL = "claude-haiku-5-5"
SYSTEM = utils.get_system_prompt()
MAX_STEPS = 100


def _prompt_only(inputs: dict) -> dict:
    """Trace the prompt, not the client: the client is a connection, not run data."""
    return {"prompt": inputs["prompt"]}


@traceable(
    name="agent",
    run_type="chain",
    tags=["anthropic-sdk", "replicablelabs-labs"],
    process_inputs=_prompt_only,
)
def main(client: Anthropic, prompt: str) -> str:
    """Run the agent on `prompt` and return its final result."""
    client = tracing.wrap_client(client)
    state = AgentState.start(prompt)
    stop_reason = None

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

        stop_reason = resp.stop_reason

        logger.debug(
            "    stop_reason=%s output_tokens=%d blocks=%s",
            resp.stop_reason,
            resp.usage.output_tokens,
            [block.type for block in resp.content],
        )

        handler = HANDLERS.get(resp.stop_reason)
        if handler(state, resp):
            break

    set_run_metadata(
        model=MODEL,
        turns=state.metadata["turns"],
        stop_reason=stop_reason,
        tool_calls=len(state.metadata["tool_calls"]),
    )
    print(state.result)
    print(state.metadata)
    return state.result
