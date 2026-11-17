"""Scripted fake of anthropic.Anthropic so loop logic is testable with no API key."""
from types import SimpleNamespace as NS

def text(t): return NS(type="text", text=t)
def tool_use(id, name, **inp): return NS(type="tool_use", id=id, name=name, input=inp)

class FakeClient:
    def __init__(self, *turns):  # each turn: (stop_reason, [blocks])
        self._turns = list(turns); self.calls = []
        self.messages = NS(create=self._create)
    def _create(self, **kw):
        kw["messages"] = list(kw["messages"]); self.calls.append(kw)
        stop, blocks = self._turns.pop(0)
        return NS(stop_reason=stop, content=blocks)
