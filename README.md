# Replicable Labs

Runnable technical demos for learning by doing.

Each exercise keeps its own installation and usage instructions in a README
inside its exercise directory.

## Run the first lab

See [`deep-agents-langgraph-101/README.md`](src/replicable/labs/deep-agents-langgraph-101/README.md)
for the complete exercise-specific setup.

Install Docker Desktop, then install this repository as a local command:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
replicable labs start deep-agents-langgraph-101
```

If this repository was already installed before an update, refresh the virtual
environment and shell command cache before retrying:

```bash
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -e .
hash -r
which replicable
```

`which replicable` should point into `.venv/bin/replicable`, not a global
`~/.local/bin/replicable` installation.

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

