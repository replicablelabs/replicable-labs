"""LangSmith tracing for this lab.

Tracing is off unless `LANGSMITH_TRACING` is truthy (see `.env.example`). Every
helper here is safe to call when tracing is off: the SDK turns the decorators
and wrappers into pass-throughs, so the agent behaves the same either way.

The project traces go to comes from `LANGSMITH_PROJECT` in the lab's `.env`
(loaded by `cli.py`). Nothing here sets it.

Pieces:
- `wrap_client(client)`: record every model call the client makes.
- `flush()`: send buffered traces before the process exits. Traces are sent by a
  background thread, so a short CLI run would otherwise exit before they leave.
"""

from langsmith.run_trees import get_cached_client
from langsmith.wrappers import wrap_anthropic


def wrap_client(client):
    """Return the Anthropic client with each `messages.create` call traced."""
    return wrap_anthropic(client)


def flush() -> None:
    """Block until queued traces are sent."""
    get_cached_client().flush()
