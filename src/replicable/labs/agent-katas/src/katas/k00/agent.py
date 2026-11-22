"""The k00 agent: the request sent to the model and the tool loop.

`uv run kata run k00 "your prompt"` calls `main(client, args)` here.
"""

import typing

from anthropic import Anthropic

from .api import request, response
from .tools import SCHEMAS, run_tool
from .utils import agent, utils
from .utils.log import logger

MODEL = "claude-haiku-5-5"
SYSTEM = utils.get_system_prompt()
MAX_STEPS = 100
MAX_TOKENS_CUTOVER_MESSAGE = utils.get_max_tokens_cutover_prompt()


def main(client: Anthropic, args: list[str]) -> None:
    """run the agent"""
    prompt = " ".join(args) or "Say hello in five words."
    max_tokens = utils.set_max_tokens_cap()
    session_metadata = {"turns": 0, "tool_calls": []}

    # agent loop
    session = []
    max_tokens_cutover_index = None  # set only while a continuation run is open
    max_tokens_capped = False
    session.append({"role": request.Role.USER, "content": prompt})
    res = ""
    for _ in range(MAX_STEPS):
        session_metadata["turns"] += 1
        logger.debug("turn %d", session_metadata["turns"])
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=session,
            system=SYSTEM,
            tools=SCHEMAS,
        )
        logger.debug(
            "    stop_reason=%s output_tokens=%d blocks=%s",
            resp.stop_reason,
            resp.usage.output_tokens,
            [block.type for block in resp.content],
        )

        # turn finalised ------------------------------------------------------
        # execute tools? Generate request message
        if resp.stop_reason == response.StopReason.TOOL_USE:
            if max_tokens_capped:
                max_tokens = utils.reset_max_tokens_cap()
                max_tokens_capped = False

            tools = [
                block
                for block in resp.content
                if block.type == response.BlockType.TOOL_USE
            ]
            tool_results = []
            for tool in tools:
                session_metadata["tool_calls"].append({tool.name: tool.input})
                content, is_error = run_tool(tool.name, tool.input)
                tool_results.append(
                    {
                        "type": request.BlockType.TOOL_RESULT,
                        "tool_use_id": tool.id,
                        "content": content,
                        "is_error": is_error,
                    }
                )

            # appending the tools results request immediately after the model response
            session.append(
                {
                    "role": request.Role.ASSISTANT,
                    "content": utils.blocks_to_dicts(resp.content),
                }
            )
            if max_tokens_cutover_index is not None:
                # this response closes a continuation run: merge it with the fragments
                merged = agent.concatenate_interrupted_responses(
                    session, max_tokens_cutover_index
                )
                session.append({"role": request.Role.ASSISTANT, "content": merged})
                max_tokens_cutover_index = None
            session.append({"role": request.Role.USER, "content": tool_results})

        elif resp.stop_reason == response.StopReason.END_TURN:
            session.append(
                {
                    "role": request.Role.ASSISTANT,
                    "content": utils.blocks_to_dicts(resp.content),
                }
            )
            if max_tokens_cutover_index is not None:
                # this response closes a continuation run: merge it with the fragments
                merged = agent.concatenate_interrupted_responses(
                    session, max_tokens_cutover_index
                )
                session.append({"role": request.Role.ASSISTANT, "content": merged})
                max_tokens_cutover_index = None

            res = "".join(
                block["text"]
                for block in session[-1]["content"]
                if block["type"] == response.BlockType.TEXT
            )
            break

        elif resp.stop_reason == response.StopReason.PAUSE_TURN:
            continue

        elif resp.stop_reason == response.StopReason.STOP_SEQUENCE:
            continue

        # turn could not finalise ---------------------------------------------
        elif resp.stop_reason == response.StopReason.MAX_TOKENS:
            # we are going to save to the session pairs (response, request) with
            # the 'continue' message, and then strip the session of these requests
            # and concatenating the responses. To do this, we are tracking the index
            # where the first response was externally interrupted.
            text_blocks_only = utils.blocks_to_dicts(
                list(
                    filter(
                        lambda block: block.type == response.BlockType.TEXT,
                        resp.content,
                    )
                )
            )
            if text_blocks_only:
                # if there was anything else in content that will have to be concatenated
                # further on
                if max_tokens_cutover_index is None:
                    # first truncation of this run: remember where it starts
                    max_tokens_cutover_index = len(session)
                session.append(
                    {"role": request.Role.ASSISTANT, "content": text_blocks_only}
                )
                session.append(
                    {
                        "role": request.Role.USER,
                        "content": MAX_TOKENS_CUTOVER_MESSAGE,
                    }
                )
            else:
                # if there were only tools, it is required to increased the max tokens cap
                max_tokens = utils.increase_max_tokens_cap(max_tokens)
                max_tokens_capped = True

        elif resp.stop_reason == response.StopReason.REFUSAL:
            # resending the same request would be refused again: stop here
            logger.error("refused: %s", resp.stop_details)
            break

        elif resp.stop_reason == response.StopReason.MODEL_CONTEXT_WINDOW_EXCEEDED:
            # the history only grows, so a retry cannot succeed: stop here
            logger.error("context window exceeded")
            break

    print(res)
    print(session_metadata)
