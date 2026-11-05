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
brew bundle --file=src/replicable/labs/deep-agents-langgraph-101/Brewfile
replicable labs start deep-agents-langgraph-101
```

The exercise's `Brewfile` declares the host-side LangSmith CLI dependency.
For hosts without Homebrew, see the exercise README for other installers.

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

The launcher prompts for an OpenAI or Anthropic provider, model, and provider
API key if needed. It also offers LangSmith browser sign-in or hidden API-key
input when no saved login is available, and enables tracing automatically. It writes
the answer to the lab's ignored `.env` file, builds the container, and opens an
interactive local chat.

The lab intentionally shows two execution layers and their traces:

- LangGraph owns the explicit `prepare -> deep_agent` workflow.
- Deep Agents owns the agentic reasoning and tool loop inside that node.
- LangSmith records the execution so you can inspect both layers.

LangSmith tracing is mandatory for this lab. The launcher enables it and
accepts a saved OAuth login profile or an API key. It mounts the profile
directory into Docker so OAuth tokens can refresh. See the lab README
for tracing destination, workspace, and regional endpoint settings.
OIDC or organization-managed sessions
can be supplied through the provider's environment variables before starting;
the launcher does not copy or print existing secrets.

