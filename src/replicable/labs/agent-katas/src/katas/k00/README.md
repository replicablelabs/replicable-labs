# k00: running the agent

k00 is a card-study agent: six tools (`create_card`, `delete_card`, `find_card`, `get_card`, `list_cards`,
`schedule_card`) over an in-memory card store. The agent code lives in [`agent.py`](agent.py).

## Prerequisites

Run everything from the lab folder (`src/replicable/labs/agent-katas`), not the repo root: `uv run` uses the nearest
`pyproject.toml`, and the repo root has no `kata` command.

```bash
cd src/replicable/labs/agent-katas
uv sync
```

Running the agent calls the real model, so it needs credentials. Pick one:

- **API key:** `cp .env.example .env` and set `ANTHROPIC_API_KEY`.
- **`ant` login:** use a profile with the inference scope, then select it in your terminal:
  ```bash
  ant auth login --profile dev --scope "user:inference"
  export ANTHROPIC_PROFILE=dev
  ```

The default `ant` login only has `org:admin`, which the API rejects for inference (403).

## Run it

```bash
uv run kata run k00 "create a card about the capital of France"
```

Everything after `k00` is joined into the prompt. With no prompt it sends "Say hello in five words."

From the repo root, add `--project`:

```bash
uv run --project src/replicable/labs/agent-katas kata run k00 "list my cards"
```

## What happens

`kata run k00` builds an `Anthropic` client and calls `main(client, args)` in `agent.py`. That function sends one
`messages.create` request (model, `max_tokens`, your prompt, the system prompt from `prompts/system.md`, and the tool
schemas) and pretty-prints the full response with `utils.show`.

As written, it makes a single request and does not execute tools: if Claude asks for one, you will see a `tool_use`
block and `stop_reason: "tool_use"` in the output. Running the tool, returning a `tool_result`, and looping until
`end_turn` is the part you build in `agent.py`.

## Things to edit

| What | Where |
|---|---|
| Model, `max_tokens`, request shape, the tool loop | `agent.py` |
| System prompt | `prompts/system.md` |
| Tool behaviour and definitions | `tools/` (one module per tool) |
| Sample cards loaded at start | `db/seed.py` |

## Test without the API

The unit tests cover the db and the tools and need no key:

```bash
uv run pytest src/katas/k00 -q
```

See [`tests/README.md`](tests/README.md) for details, and [`docs/tool_design.md`](docs/tool_design.md) for the tool
conventions.
