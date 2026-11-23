# anthropic-sdk

A sandbox for learning the Anthropic Messages API by building a tool-use agent: a card-study assistant with six tools
(`create_card`, `delete_card`, `find_card`, `get_card`, `list_cards`, `schedule_card`) over an in-memory card store.
Raw `anthropic` SDK and `pydantic` only: no frameworks, no databases.

> **Run every command from this lab folder**, not the repo root. `uv run` uses the nearest `pyproject.toml`; at the repo root that is
> the *other* project, which has no `kata` command. From the repo root you can instead use
> `uv run --project src/replicable/labs/anthropic-sdk kata ...`.

## Setup

```bash
cd src/replicable/labs/anthropic-sdk     # from the repo root
uv sync
cp .env.example .env                   # only needed for `kata run`; the tests need no key
```

**Authentication (only for `kata run`, which calls the model).** Either set `ANTHROPIC_API_KEY` in `.env`, or sign in with the `ant` CLI
using an *inference* scope and select that profile:
```bash
ant auth login --profile dev --scope "user:inference"
export ANTHROPIC_PROFILE=dev           # per terminal
```
The default `ant` login only has `org:admin`, which the API rejects for inference (`403 ... OAuth token does not meet scope requirement`).

## Use

```bash
uv run kata run k00 "create a card about the capital of France, then schedule it for tomorrow at 9"
uv run pytest k00 -q         # unit tests for the db and the tools (no API key needed)
```

`kata run k00` calls `main(client, args)` in `k00/agent.py`. Output is coloured on a terminal
(`NO_COLOR` disables it, `FORCE_COLOR` forces it).

## Layout

```
cli.py, style.py       the `kata run` command and colour helpers
k00/
  agent.py           entry point: the request you send to the model, the loop
  state.py           AgentState: what the loop and the handlers share
  handlers/          one module per stop_reason (tool_use, end_turn, max_tokens, ...)
  prompts/system.md  system prompt
  tools/             one module per tool; each @tool docstring is the tool definition
    schemas.py       pydantic contract for tool results
    base.py          @tool wrapper that serialises the result model
  db/                in-memory card store (models, store, search, seed)
  utils/             ToolError, helpers
  docs/              notes: tool design, system prompt checklist, evals
  tests/             no API key needed
    conftest.py      fresh db per test, `call` fixture for running a tool
    db/              store (ids, reset, delete) and search
    tools/           one file per tool, or per group of read-only tools, plus the tool runner
    test_schemas.py  each tool definition matches its code
```

Run one area with e.g. `uv run pytest k00/tests/tools/test_create_card.py`.

Start with `k00/docs/tool_design.md`: it explains the layout and the tool conventions in detail.
