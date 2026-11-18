"""KATA 4 (from scratch) - reliable structured output. Run:  uv run kata test k04

classify_ticket(client, text, model=MODEL) -> {"category": billing|shipping|account|other, "urgency": low|medium|high, "needs_human": bool}
  Use Anthropic tool use so the model is forced to answer through a tool named TOOL_NAME with an enum JSON schema. Validate what
  comes back; if invalid, tell the model (as a tool_result error) and retry once; after that raise ValueError.
  Read tests/test_k04.py for exact expectations.
"""
import os

MODEL = os.environ.get("KATA_MODEL", "claude-sonnet-5-5")
TOOL_NAME = "record_classification"

def classify_ticket(client, text: str, model: str = MODEL) -> dict:
    raise NotImplementedError
