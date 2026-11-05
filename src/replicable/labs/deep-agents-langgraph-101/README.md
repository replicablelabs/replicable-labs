# Deep Agents + LangGraph 101

This lab shows how a LangGraph workflow can contain a Deep Agent as one of its
nodes. The outer graph owns explicit workflow control; the inner Deep Agent
owns agentic reasoning and tool use. LangSmith tracing is required so you can
inspect both layers as you learn.

## Requirements

- Docker Desktop
- Python 3.9 or newer for the Replicable launcher
- For OpenAI: a ChatGPT account eligible for plan usage, or an OpenAI API key
- For Anthropic: an Anthropic API key
- A LangSmith account with browser login (OAuth) or an API key, and access
  to a tracing destination
- The official LangSmith CLI (v0.2.30 or newer) for browser login, declared
  as a host dependency in this exercise's `Brewfile`

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
- for OpenAI, authentication by `browser` (ChatGPT sign-in) or `api-key`
- the model name (browser mode lists models available to the signed-in account)
- the provider API key when using API-key authentication and no key is available
- LangSmith sign-in (`browser` or `api-key`) when no saved login is available

For OpenAI, choose `browser` to use **Continue with ChatGPT**. The launcher
opens the browser and asks you to allow ChatGPT plan usage. It verifies the
returned identity, saves this lab's own registration and session under the
ignored `.data/openai/` directory, and lists the account's available models.
The session directory is mounted into Docker so expired tokens can refresh.
No OpenAI API key is needed in this mode. Account eligibility, consent, and
plan usage limits still apply.

Choose `api-key` to enter a provider API key through a hidden prompt. Existing
keys in your environment or lab settings select API-key mode automatically.
A blank key stops startup in that mode. Anthropic uses API-key mode.

LangSmith has its own separate sign-in prompt. Its browser login authorizes
tracing; OpenAI browser login authorizes model calls.

It saves local settings to this exercise's ignored `.env` file, builds the
Docker image, and opens an interactive chat. Type `exit` to stop.
Tracing is always enabled by the launcher, including for existing `.env`
files that previously disabled it. The app enables tracing automatically too;
there is no need to set `LANGSMITH_TRACING` manually. Complete LangSmith
sign-in before the container starts.

## Choose or switch OpenAI authentication

The launcher remembers the selected authentication mode. You can override it
for the next launch:

```bash
replicable labs start deep-agents-langgraph-101 --auth browser
replicable labs start deep-agents-langgraph-101 --auth api-key
```

Browser mode always uses the lab's ChatGPT session, even if an API key is also
present. It does not read Codex credentials or Replicable's existing connections.
Returning sign-in reuses this lab's issued client ID and stable host ID.
Tokens are stored in a file readable only by its owner and never in `.env` or
the image. To reconnect after a revoked session, run:

```bash
replicable labs start deep-agents-langgraph-101 --auth browser --login
```

The lab retains its registration when you reconnect. You can also set
`OPENAI_AUTH_MODE=browser` or `api-key` in your shell.

This uses Replicable's Improve connection as the reference: authorization
code with PKCE, OIDC identity verification, consent for ChatGPT plan usage,
rotating refresh tokens, and the public Responses API. Browser requests always
stream with `store=false`; incomplete or interrupted streams raise an error.
There is no automatic switch to API-key billing if browser authentication fails.
See the official [Sign in with ChatGPT guide](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
and [models and inference contract](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).

## Existing API keys

Set the provider variables before starting if you already have a credential
connection configured:

```bash
export MODEL_PROVIDER=openai
export MODEL_NAME=gpt-4.1-mini
export OPENAI_API_KEY="$YOUR_EXISTING_CREDENTIAL"
```

For Anthropic, use `ANTHROPIC_API_KEY` instead. The launcher does not print
existing keys or overwrite them. OpenAI browser sign-in is described above;
LangSmith browser login is configured separately below.

## Required LangSmith setup

1. Install the exercise's host dependencies from the repository root.
   On macOS with Homebrew:

   ```bash
   brew bundle --file=src/replicable/labs/deep-agents-langgraph-101/Brewfile
   ```

   The `Brewfile` installs the official LangSmith CLI on the host, where
   browser login runs. Python dependencies for the container are declared
   separately in `requirements.txt`. For hosts without Homebrew, use the
   official [CLI installation instructions](https://docs.langchain.com/langsmith/langsmith-cli).

2. Start the lab and choose `browser` at the LangSmith sign-in prompt.
   The launcher runs the browser login for you. You can also sign in ahead
   of time:

   ```bash
   langsmith auth login
   ```

   This uses OAuth device authorization and saves a local login profile.
   You can use your organization's SSO during browser sign-in when available.
   An API key is not required for this path. To choose a profile explicitly,
   use `langsmith auth login --profile dev` and `export LANGSMITH_PROFILE=dev`.

3. Select a tracing destination for your workspace:
   - In an agent-based workspace, create an Observability agent in LangSmith,
     then export its Agent ID and environment before starting:

     ```bash
     export LANGSMITH_AGENT_ID="<your-agent-id>"
     export LANGSMITH_AGENT_ENVIRONMENT=local
     ```

   - In a project-based workspace, leave `LANGSMITH_AGENT_ID` unset. The lab
     uses the project `replicable-deep-agents-langgraph-101`, or the name set
     in `LANGSMITH_PROJECT`.

The app removes legacy project settings when an Agent ID is configured, as
LangSmith requires these addressing modes to be separate.

The launcher mounts the login profile's directory into the container so the
Python SDK can use and refresh its OAuth tokens. Tokens stay in the profile;
they are not copied into the lab's `.env` file or container image. A custom
host profile path can be supplied through `LANGSMITH_CONFIG_FILE`.
The lab requires Python SDK `langsmith>=0.8.1` for profile support.
An explicit `LANGSMITH_API_KEY` takes precedence over a login profile. To use
browser login, unset that variable and remove any saved LangSmith API key
from the lab's `.env` file.
If you invoke Compose directly, mount the profile directory yourself at
`/run/langsmith-profile`, or supply an API key.

Alternatively, choose `api-key` at the launcher prompt for hidden input,
or supply an API key in your shell:

```bash
export LANGSMITH_API_KEY="$YOUR_LANGSMITH_KEY"
```

For an EU LangSmith account, also set
`LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com`. For other regions,
use the API endpoint for that deployment. Leave the endpoint unset to use
the region saved in your login profile. If your key is scoped to multiple
workspaces, set `LANGSMITH_WORKSPACE_ID` to the intended workspace ID.
These settings are forwarded to the container.

Tracing sends the lab's inputs, outputs, and execution details to your
LangSmith workspace. Startup checks configuration; a successful first trace
confirms that the credentials, destination, and endpoint work together.
Self-hosted browser login requires CLI v0.2.46 or newer and LangSmith 0.16
or newer with its OAuth authorization server enabled; other installations
can use API-key authentication.

See the official [profile and OAuth setup](https://docs.langchain.com/langsmith/profile-configuration),
[account and API key setup](https://docs.langchain.com/langsmith/create-account-api-key)
and [LangGraph tracing guide](https://docs.langchain.com/langsmith/trace-with-langgraph).

## First tracing exercise

Ask: `Use explain_concept to explain LangGraph from the local notes.`
Then open the latest trace in your LangSmith agent/environment or tracing project:

1. Find the outer graph's `prepare` and `deep_agent` steps.
2. Expand `deep_agent` to inspect the nested model calls and any tool calls.
3. Compare each step's inputs, outputs, and duration. Inspect token usage
   where the model provider reports it.

Tool calls are model decisions, so inspect what actually ran. The graph
always orders `prepare` before `deep_agent`; LangSmith records that execution.

## If no container starts

Run the command from the repository's virtual environment:

```bash
source .venv/bin/activate
hash -r
which replicable
replicable labs start deep-agents-langgraph-101
```

`which replicable` must point to this checkout's `.venv/bin/replicable`.
A global `~/.local/bin/replicable` may belong to an older or different
installation and can fail before reaching Docker. Complete the provider
and LangSmith prompts; only then does the container start.

The lab runs as an attached, interactive container. Type `exit` to stop it;
Docker removes the container when the session ends.

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

