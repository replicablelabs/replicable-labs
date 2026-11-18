"""A STRICT fake of anthropic.Anthropic: it validates message structure the way the real API does, so loop bugs fail loudly.
Rules enforced: every tool_use in an assistant message needs a tool_result for EACH id in the NEXT user message
(one message, not one per result); a tool_result must answer a tool_use in the previous assistant message; no empty content."""
from types import SimpleNamespace as NS

class BadRequest(Exception): pass

def text(t): return NS(type="text", text=t)
def tool_use(id, name, **inp): return NS(type="tool_use", id=id, name=name, input=inp)

def _g(b, k): return b[k] if isinstance(b, dict) else getattr(b, k)

def validate_messages(messages):
    if not messages or messages[0]["role"] != "user": raise BadRequest("first message must have role 'user'")
    for i, m in enumerate(messages):
        c = m["content"]
        if isinstance(c, str):
            if not c: raise BadRequest(f"message {i}: empty content")
            continue
        if not c: raise BadRequest(f"message {i}: empty content list (did you drop the assistant's tool_use blocks?)")
        if m["role"] == "assistant":
            ids = [_g(b, "id") for b in c if _g(b, "type") == "tool_use"]
            if not ids: continue
            nxt = messages[i + 1] if i + 1 < len(messages) else None
            got = [_g(b, "tool_use_id") for b in (nxt["content"] if nxt and nxt["role"] == "user" and not isinstance(nxt["content"], str) else []) if _g(b, "type") == "tool_result"]
            if sorted(got) != sorted(ids):
                raise BadRequest(f"message {i}: tool_use ids {sorted(ids)} must be answered by tool_result blocks for exactly those ids "
                                 f"in ONE following user message; got {sorted(got)}")
        else:
            res = [_g(b, "tool_use_id") for b in c if _g(b, "type") == "tool_result"]
            if res:
                prev = messages[i - 1] if i else None
                prev_ids = {_g(b, "id") for b in (prev["content"] if prev and prev["role"] == "assistant" else []) if _g(b, "type") == "tool_use"}
                if not set(res) <= prev_ids:
                    raise BadRequest(f"message {i}: tool_result for ids {sorted(set(res) - prev_ids)} with no matching tool_use in the previous assistant message")

class FakeClient:
    """FakeClient(("tool_use", [tool_use(...)]), ("end_turn", [text("ok")])). repeat_last=True repeats the final turn forever."""
    def __init__(self, *turns, repeat_last=False, max_calls=30):
        self._turns, self._repeat, self._max = list(turns), repeat_last, max_calls
        self.calls = []
        self.messages = NS(create=self._create)
    def _create(self, **kw):
        kw["messages"] = list(kw["messages"])
        validate_messages(kw["messages"])
        self.calls.append(kw)
        if len(self.calls) > self._max: raise AssertionError("agent never stopped (infinite loop)")
        turn = self._turns.pop(0) if len(self._turns) > 1 or not self._repeat else self._turns[0]
        stop, blocks = turn
        return NS(stop_reason=stop, content=blocks)
