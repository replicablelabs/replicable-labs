"""KATA 1 - the agent loop. This implementation has several bugs. Fix them so tests/test_k01.py passes.
Read the failing test names and the BadRequest messages: the fake client validates messages like the real API."""

import os
from dataclasses import dataclass

MODEL = os.environ.get("KATA_MODEL", "claude-sonnet-5-5")


@dataclass
class Result:
    answer: str
    steps: int
    stop: str


def run_agent(
    question, client, schemas, impls, system="", max_steps=8, model=MODEL
) -> Result:
    messages = [{"role": "user", "content": question}]
    for step in range(100):
        resp = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            tools=schemas,
            messages=messages,
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        messages.append(
            {
                "role": "assistant",
                "content": [b for b in resp.content if b.type == "text"],
            }
        )
        if resp.stop_reason != "tool_use":
            return Result(text, step + 1, resp.stop_reason)
        for block in resp.content:
            if block.type == "tool_use":
                out = impls[block.name](**block.input)
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": out,
                            }
                        ],
                    }
                )
    return Result(text, max_steps, "max_steps")
