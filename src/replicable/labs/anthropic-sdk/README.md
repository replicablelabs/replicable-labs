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

## Run it

```bash
uv run kata run "create a card about the capital of France, then schedule it for tomorrow at 9"
uv run pytest -q                       # unit tests for the db, the tools and the handlers (no API key needed)
```

Everything after `run` is joined into the prompt. With no prompt it sends "Hello, world?" Output is coloured on a
terminal (`NO_COLOR` disables it, `FORCE_COLOR` forces it). Set `DEBUG=1` for a turn-by-turn log on stderr.

## What happens

`kata run` builds an `Anthropic` client and calls `main(client, args)` in [`agent.py`](agent.py). The loop sends one
`messages.create` request per turn (model, `max_tokens`, the conversation so far, the system prompt from `prompts/system.md`,
and the tool schemas), then dispatches on `stop_reason` to a handler in [`handlers/`](handlers):

| `stop_reason` | What the handler does |
|---|---|
| `tool_use` | runs the tools and sends the `tool_result` blocks back |
| `end_turn` | takes the text as the final answer and stops |
| `max_tokens` | discards the truncated response, doubles the cap (up to the model's output limit) and resends |
| `refusal`, `model_context_window_exceeded` | logs the reason and stops |
| `pause_turn`, `stop_sequence` | not handled yet |
| anything else | logs the value and stops |

`max_tokens` has a second recovery, stitching (keep the text, send "continue", merge the fragments). It is off by default
because it is unreliable; `MAX_TOKENS_STRATEGY=continue` turns it on.

## Things to edit

| What | Where |
|---|---|
| Model, `max_tokens`, request shape, the loop | `agent.py` |
| What each stop reason does | `handlers/` |
| System prompt | `prompts/system.md` |
| Tool behaviour and definitions | `tools/` (one module per tool) |
| Sample cards loaded at start | `db/seed.py` |

## Layout

```
cli.py, style.py     the `kata run` command and colour helpers
agent.py             entry point: the request you send to the model, the loop
state.py             AgentState: what the loop and the handlers share
handlers/            one module per stop_reason (tool_use, end_turn, max_tokens, ...)
api/                 StrEnums for the request and response values
prompts/system.md    system prompt
tools/               one module per tool; each @tool docstring is the tool definition
  schemas.py         pydantic contract for tool results
  base.py            @tool wrapper that serialises the result model
db/                  in-memory card store (models, store, search, seed)
utils/               ToolError, logging, helpers
docs/                notes: tool design, system prompt checklist, evals
evals/               offline evals: call the real model, run with `uv run python -m evals.run`
  cases/             inputs and expected results (LangSmith dataset examples)
  graders.py         functions that judge a run
  run.py             runs the cases as a LangSmith experiment
  config.py          sends traces to LANGSMITH_EVALS_PROJECT
tests/               no API key needed
  conftest.py        fresh db per test, `call` fixture for running a tool
  db/                store (ids, reset, delete) and search
  tools/             one file per tool, or per group of read-only tools, plus the tool runner
  handlers/          one file per stop-reason handler
  api/, utils/       enums and helpers
  test_*.py          the loop, cli, state, style, tracing
  test_schemas.py    each tool definition matches its code
```

The code is flat, so these install as top-level modules (`agent`, `tools`, `utils`, ...).

Run one area with e.g. `uv run pytest tests/tools/test_create_card.py`. See [`tests/README.md`](tests/README.md) for details and
[`docs/tool_design.md`](docs/tool_design.md) for the tool conventions.
