"""The k00 agent: the request sent to the model and the tool loop.

`uv run kata run k00 "your prompt"` calls `main(client, args)` here.
"""

import typing

from anthropic import Anthropic

from .api import request, response
from .tools import SCHEMAS, run_tool
from .utils import agent, utils

MODEL = "claude-haiku-5-5"
SYSTEM = utils.get_system_prompt()
MAX_STEPS = 100


def main(client: Anthropic, args: list[str]) -> None:
    """run the agent"""
    prompt = " ".join(args) or "Say hello in five words."
    max_tokens = utils.set_max_tokens()
    session_metadata = {"turns": 0, "tool_calls": []}

    # agent loop
    session = []
    max_tokens_cutover = len(session)
    session.append({"role": request.Role.USER, "content": prompt})
    res = ""
    for _ in range(MAX_STEPS):
        session_metadata["turns"] += 1
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=session,
            system=SYSTEM,
            tools=SCHEMAS,
        )

        # turn finalised ------------------------------------------------------
        # execute tools? Generate request message
        if resp.stop_reason == response.StopReason.TOOL_USE:
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
            session.append({"role": request.Role.ASSISTANT, "content": resp.content})
            session.append({"role": request.Role.USER, "content": tool_results})

        elif resp.stop_reason == response.StopReason.END_TURN:
            utils.show(resp)
            res = [
                block.text
                for block in resp.content
                if block.type == response.BlockType.TEXT
            ]
            break

        elif resp.stop_reason == response.StopReason.PAUSE_TURN:
            continue

        elif resp.stop_reason == response.StopReason.STOP_SEQUENCE:
            continue

        # turn could not finalise ---------------------------------------------
        elif resp.stop_reason == response.StopReason.MAX_TOKENS:
            max_tokens_cutover = len(session)
            concatenate_content = agent.concatenate_interrupted_responses(
                session, max_tokens_cutover
            )
            session.append(
                {"role": request.Role.ASSISTANT, "content": concatenate_content}
            )
            session.append(
                {
                    "role": request.Role.USER,
                    "content": "continue exactly from where you left off",
                }
            )

        elif resp.stop_reason == response.StopReason.REFUSAL:
            pass

        elif resp.stop_reason == response.StopReason.MODEL_CONTEXT_WINDOW_EXCEEDED:
            pass

    print(res)
    print(session_metadata)
