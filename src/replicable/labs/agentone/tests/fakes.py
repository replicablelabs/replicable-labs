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

class FakeOpenAI:
    """Scripted openai.OpenAI: each turn is (finish_reason, content, [(id,name,json_args)])."""
    def __init__(self, *turns):
        self._turns = list(turns); self.calls = []
        self.chat = NS(completions=NS(create=self._create))
    def _create(self, **kw):
        kw["messages"] = list(kw["messages"]); self.calls.append(kw)
        fin, content, tcs = self._turns.pop(0)
        calls = [NS(id=i, function=NS(name=n, arguments=a)) for i, n, a in tcs] or None
        return NS(choices=[NS(finish_reason=fin, message=NS(content=content, tool_calls=calls))])
