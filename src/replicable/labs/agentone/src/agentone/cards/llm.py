"""Provider-agnostic LLM interface. `structured` = schema-constrained output validated by pydantic (retry once)."""
from __future__ import annotations
import os
from typing import Protocol, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

class LLM(Protocol):
    def text(self, system: str, messages: list[dict]) -> str: ...
    def structured(self, system: str, user: str, schema: type[T]) -> T: ...

class AnthropicLLM:
    def __init__(self, client=None, model: str | None = None):
        import anthropic
        self.client = client or anthropic.Anthropic()
        self.model = model or os.environ.get("AGENTONE_MODEL", "claude-sonnet-5-5")

    def text(self, system, messages):
        r = self.client.messages.create(model=self.model, max_tokens=1024, system=system, messages=messages)
        return "".join(b.text for b in r.content if b.type == "text")

    def structured(self, system, user, schema):
        err: Exception | None = None
        for _ in range(2):
            r = self.client.messages.create(
                model=self.model, max_tokens=1024, system=system,
                messages=[{"role": "user", "content": user}],
                tools=[{"name": "emit", "description": "Return the result.", "input_schema": schema.model_json_schema()}],
                tool_choice={"type": "tool", "name": "emit"})  # forced tool call == JSON-schema output
            block = next(b for b in r.content if b.type == "tool_use")
            try: return schema.model_validate(block.input)
            except ValidationError as e: err = e; user += f"\n\nYour previous output was invalid: {e}. Fix it."
        raise err  # type: ignore[misc]

class OpenAILLM:
    def __init__(self, client=None, model: str | None = None):
        from openai import OpenAI
        self.client = client or OpenAI()
        self.model = model or os.environ.get("AGENTONE_OPENAI_MODEL", "gpt-4.1")

    def text(self, system, messages):
        r = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system}, *messages])
        return r.choices[0].message.content or ""

    def structured(self, system, user, schema):
        sys = f"{system}\nRespond with a single JSON object matching this JSON schema:\n{schema.model_json_schema()}"
        err: Exception | None = None
        for _ in range(2):
            r = self.client.chat.completions.create(
                model=self.model, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}])
            try: return schema.model_validate_json(r.choices[0].message.content or "{}")
            except ValidationError as e: err = e; user += f"\n\nYour previous JSON was invalid: {e}. Fix it."
        raise err  # type: ignore[misc]

def get_llm(role) -> LLM:
    """role: config.ChatModel (provider + model)."""
    return {"anthropic": AnthropicLLM, "openai": OpenAILLM}[role.provider](model=role.model)
