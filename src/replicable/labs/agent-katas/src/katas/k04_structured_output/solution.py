import os

MODEL = os.environ.get("KATA_MODEL", "claude-sonnet-5-5")
TOOL_NAME = "record_classification"
CATEGORIES = ["billing", "shipping", "account", "other"]
URGENCY = ["low", "medium", "high"]
SCHEMA = {"type": "object", "properties": {
    "category": {"type": "string", "enum": CATEGORIES},
    "urgency": {"type": "string", "enum": URGENCY, "description": "high = money lost or customer blocked right now"},
    "needs_human": {"type": "boolean", "description": "true if an agent cannot resolve this with the available tools"}},
    "required": ["category", "urgency", "needs_human"]}
SYSTEM = "You classify customer-support tickets. Always answer by calling record_classification."

def _validate(x: dict) -> str | None:
    if x.get("category") not in CATEGORIES: return f"category must be one of {CATEGORIES}, got {x.get('category')!r}"
    if x.get("urgency") not in URGENCY: return f"urgency must be one of {URGENCY}, got {x.get('urgency')!r}"
    if not isinstance(x.get("needs_human"), bool): return "needs_human must be a boolean"
    return None

def classify_ticket(client, text: str, model: str = MODEL, retries: int = 1) -> dict:
    tools = [{"name": TOOL_NAME, "description": "Record the classification of a support ticket.", "input_schema": SCHEMA}]
    messages = [{"role": "user", "content": f"Classify this support ticket:\n\n{text}"}]
    err = "no attempt made"
    for _ in range(retries + 1):
        resp = client.messages.create(model=model, max_tokens=300, system=SYSTEM, tools=tools,
                                      tool_choice={"type": "tool", "name": TOOL_NAME}, messages=messages)   # forces the schema
        block = next(b for b in resp.content if b.type == "tool_use")
        err = _validate(block.input)
        if err is None: return dict(block.input)
        messages += [{"role": "assistant", "content": resp.content},
                     {"role": "user", "content": [{"type": "tool_result", "tool_use_id": block.id, "content": err, "is_error": True}]}]
    raise ValueError(f"invalid classification after {retries + 1} attempts: {err}")
