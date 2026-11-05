# Replicable Labs

Runnable technical demos for learning by doing.

## Run the first lab

Install Docker Desktop, then install this repository as a local command:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
replicable labs start deep-agents-langgraph-101
```

The launcher prompts for an OpenAI or Anthropic provider, model, and API key if
the corresponding environment variable is not already available. It writes
the answer to the lab's ignored `.env` file, builds the container, and opens an
interactive local chat.

The lab intentionally shows two layers:

- LangGraph owns the explicit `prepare -> deep_agent` workflow.
- Deep Agents owns the agentic reasoning and tool loop inside that node.

For tracing, set `LANGSMITH_TRACING=true` and provide `LANGSMITH_API_KEY` when
the launcher prompts for configuration. OIDC or organization-managed sessions
can be supplied through the provider's environment variables before starting;
the launcher does not copy or print existing secrets.

