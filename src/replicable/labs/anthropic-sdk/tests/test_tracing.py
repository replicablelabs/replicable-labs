"""LangSmith helpers. The LangSmith SDK is replaced, so nothing leaves the machine."""

from unittest.mock import Mock

import tracing


def test_wrap_client_returns_the_traced_client(monkeypatch):
    """The agent gets LangSmith's wrapped client, built from the one it passed in."""
    wrap = Mock()
    monkeypatch.setattr(tracing, "wrap_anthropic", wrap)
    client = object()

    assert tracing.wrap_client(client) is wrap.return_value

    wrap.assert_called_once_with(client)


def test_flush_waits_for_queued_traces(monkeypatch):
    """Flushing is passed on to the LangSmith client that holds the queue."""
    langsmith = Mock()
    monkeypatch.setattr(tracing, "get_cached_client", lambda: langsmith)

    tracing.flush()

    langsmith.flush.assert_called_once_with()
