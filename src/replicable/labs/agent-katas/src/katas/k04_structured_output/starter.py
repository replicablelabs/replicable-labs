"""KATA 4 - reliable structured output. classify_ticket must return
{"category": billing|shipping|account|other, "urgency": low|medium|high, "needs_human": bool}.
This version asks for JSON in free text and parses it. Make it robust using Anthropic tool use (see tests/test_k04.py)."""
import json, os

MODEL = os.environ.get("KATA_MODEL", "claude-sonnet-5-5")
TOOL_NAME = "record_classification"

def classify_ticket(client, text: str, model: str = MODEL) -> dict:
    resp = client.messages.create(model=model, max_tokens=300, messages=[
        {"role": "user", "content": f"Classify this support ticket. Reply with JSON only.\n\n{text}"}])
    return json.loads(resp.content[0].text)
