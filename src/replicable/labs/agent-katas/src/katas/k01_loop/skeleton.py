"""KATA 1 (from scratch) - write the agent loop yourself. Run:  uv run kata test k01

Contract (tests/test_k01.py checks all of this):
  run_agent(question, client, schemas, impls, system="", max_steps=8, model=MODEL) -> Result(answer, steps, stop)
  - client.messages.create(model=, max_tokens=, system=, tools=schemas, messages=) is the Anthropic call
  - schemas = list of tool JSON schemas; impls = {tool_name: python_callable(**input) -> str}
  - loop until the model stops asking for tools; `stop` is the model's stop_reason, or "max_steps" if you hit the cap
  - answer = all text blocks of the final response joined
  - the API is strict about message structure: the fake client in tests raises BadRequest the way the real API would
  - tools can fail or be unknown: the model should be told, the program must not crash
"""
import os
from dataclasses import dataclass

MODEL = os.environ.get("KATA_MODEL", "claude-sonnet-5-5")

@dataclass
class Result:
    answer: str
    steps: int
    stop: str

def run_agent(question, client, schemas, impls, system="", max_steps=8, model=MODEL) -> Result:
    raise NotImplementedError
