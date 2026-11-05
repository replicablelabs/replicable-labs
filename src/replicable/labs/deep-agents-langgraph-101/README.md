# Deep Agents + LangGraph 101

This lab shows how a LangGraph workflow can contain a Deep Agent as one of its
nodes. The outer graph owns explicit workflow control; the inner Deep Agent
owns agentic reasoning and tool use.

## Requirements

- Docker Desktop
- Python 3.9 or newer for the Replicable launcher
- An OpenAI or Anthropic API key, unless the required provider credential is
  already available through your local environment or organization setup

The demo itself runs in a Python 3.11 Docker container, so the host Python is
only used to install and run the launcher.

## Install the launcher

From the root of the cloned `replicable-labs` repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Start the lab

```bash
replicable labs start deep-agents-langgraph-101
```

The launcher prompts for:

- `openai` or `anthropic`
- the model name
- the provider API key when it is not already available

It saves local settings to this exercise's ignored `.env` file, builds the
Docker image, and opens an interactive chat. Type `exit` to stop.

## Existing or organization-managed credentials

Set the provider variables before starting if you already have a credential
connection configured:

```bash
export MODEL_PROVIDER=openai
export MODEL_NAME=gpt-4.1-mini
export OPENAI_API_KEY="$YOUR_EXISTING_CREDENTIAL"
```

For Anthropic, use `ANTHROPIC_API_KEY` instead. The launcher does not print
existing credentials or overwrite them. Browser-based OIDC login is not part
of this first lab; provide the resulting provider credential through the
environment instead.

## Optional tracing

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY="$YOUR_LANGSMITH_KEY"
```

## If an older install is still being used

Refresh the virtual environment and shell command cache:

```bash
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -e .
hash -r
which replicable
```

`which replicable` should point to `.venv/bin/replicable`, not a global
`~/.local/bin/replicable` installation.

