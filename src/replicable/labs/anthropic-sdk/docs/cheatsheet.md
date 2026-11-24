# Cheatsheet

## LangSmith

**Trace** = a tree of **runs**. The root run is one call to a traced function; calls made inside it become child runs.

**Run types** (`run_type`):
- `chain`: coordinates other steps (`main()`)
- `tool`: one action the model asked for, run by our code (`run_tool`)
- `llm`: a model call (added automatically by `wrap_anthropic`)
- also: `retriever`, `embedding`, `prompt`, `parser`

**Setup** (`.env`, loaded by `cli.py`):
- `LANGSMITH_API_KEY`: secret, never committed
- `LANGSMITH_TRACING=true|false`: off means decorators and wrappers do nothing
- `LANGSMITH_PROJECT`: where traces go; unset means LangSmith's `default` project

**Tools in this lab:**
- `@traceable(name=, run_type=, tags=, process_inputs=)`: traces a function
  - `process_inputs(inputs: dict) -> dict`: edit what gets recorded; keys are parameter names
- `set_run_metadata(**kw)`: attach key/values to the current run (inside a traced function)
- `wrap_anthropic(client)`: traces every `messages.create` call (tokens, latency, inputs, outputs)
- `get_cached_client().flush()`: send queued traces; traces go out on a background thread, so flush before a short process exits

**Watch out:**
- Traces store prompts and responses. Keep secrets out of them.
- Tests set `LANGSMITH_TRACING=false` (see `tests/conftest.py`).

**Offline evals** (planned, not built yet): dataset of inputs (+ expected outputs) → target function (calls `main`) → evaluators (code checks or LLM judge, return a score) → run `evaluate(...)` → compare experiments in the UI.

## Anthropic Messages API

**Request**: `client.messages.create(model, max_tokens, messages, system, tools)`
- `max_tokens`: required; caps output length
- `system`: top-level string. Not a message role.
- `messages`: list of `{"role": "user" | "assistant", "content": ...}`
  - first message must be `user`; roles alternate
  - `content` is a **string** or a **list of block objects**. A list of plain strings is rejected with `messages.0.content.0: Input should be an object`.
- `tools`: list of `{"name", "description", "input_schema"}` (JSON Schema)

**Blocks you send**:
- text: `{"type": "text", "text": "..."}`
- tool result (in a `user` message): `{"type": "tool_result", "tool_use_id": "<id>", "content": "<string>", "is_error": false}`
- every `tool_use` in an assistant turn needs a matching `tool_result` in the next user message

**Response**: `resp.stop_reason`, `resp.content` (list of blocks), `resp.usage.input_tokens`, `resp.usage.output_tokens`
- block types: `text` (`.text`), `tool_use` (`.id`, `.name`, `.input` as a dict), `thinking`
- response blocks are SDK objects; convert to dicts before putting them back in `messages`

**Stop reasons** (what the loop does next, from `api/response.py` and `handlers/`):

| `stop_reason` | Meaning | Our handler |
|---|---|---|
| `tool_use` | run the requested tools, send results back | run tools, loop |
| `end_turn` | final answer | stop |
| `max_tokens` | cut off mid-output | retry with a bigger limit (never run tools from this) |
| `pause_turn` | long server-side turn paused | resend history as is |
| `stop_sequence` | hit one of your `stop_sequences` | depends on design |
| `refusal` | declined for safety | stop and report; retrying won't help |
| `model_context_window_exceeded` | history too long | stop; shorten history first |

**Loop shape**: send request → get response → read `stop_reason` → dispatch to handler → append assistant content and tool results → repeat, capped by `MAX_STEPS`.

# Do Not Forget

## Returning tool results

Returning tool results requires contract:

```json
tool_results.append(
    {
        "type": request.BlockType.TOOL_RESULT,
        "tool_use_id": block.id,
        "content": content,
        "is_error": is_error,                   # <-- IMPORTANT
    }
)
```

is `is_error` the content should explain what went wrong.

## Pydantic

```python
from pydantic import BaseModel, Field

# tools/schemas.py
class Card(BaseModel):
    """A card as shown to the model. Unset fields are left out of the JSON."""

    id: str
    title: str
    content: Optional[str] = None
    scheduled_at: Optional[str] = None
    score: Optional[float] = None  # only on find_card results
```

## LangSmith

Tracing `run_tool` for our tool executions (`tool`), all request/response exchanges (`wrap_client`), and the agent run (for grouping `chain`)

```python
from langsmith import traceable

# agent.py
@traceable(
    name="agent",
    run_type="chain", # <-- run_type CHAIN
    tags=["anthropic-sdk", "replicablelabs-labs"],
    process_inputs=_prompt_only,
    process_outputs=_result_only,
)
def run(client: Anthropic, prompt: str) -> AgentState:
    ...

# tools/__init__.py
@traceable(run_type="tool") # <-- run_type TOOL
def run_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    ...

# tracing.py
from langsmith.run_trees import get_cached_client
from langsmith.wrappers import wrap_anthropic


def wrap_client(client):
    """Return the Anthropic client with each `messages.create` call traced."""
    return wrap_anthropic(client)


def flush() -> None:
    """Block until queued traces are sent."""
    get_cached_client().flush()
```

## Agent Loop

```python
@traceable(
    name="agent",
    run_type="chain",
    tags=["anthropic-sdk", "replicablelabs-labs"],
    process_inputs=_prompt_only, # <-- into langsmith
    process_outputs=_result_only, # <-- into langsmith
)
def run(client: Anthropic, prompt: str) -> AgentState:
    """Run the agent on `prompt` and return its final state."""
    client = tracing.wrap_client(client)
    state = AgentState.start(prompt)

    for _ in range(MAX_STEPS):
        # A step is one request, retries included; MAX_STEPS caps steps.
        state.metadata["steps"] += 1
        logger.debug(
            "turn %d step %d", state.metadata["turns"], state.metadata["steps"]
        )

        resp = client.messages.create(
            model=MODEL,
            max_tokens=state.max_tokens,
            messages=state.session,
            system=SYSTEM,
            tools=SCHEMAS,
        )

        state.stop_reason = resp.stop_reason
        # A turn is a step whose response completes a turn; discarded retries don't count.
        if state.stop_reason in COMPLETED_TURN_REASONS:
            state.metadata["turns"] += 1

        logger.debug(
            "    stop_reason=%s output_tokens=%d blocks=%s",
            resp.stop_reason,
            resp.usage.output_tokens,
            [block.type for block in resp.content],
        )

        handler = HANDLERS.get(resp.stop_reason, on_unknown)
        if handler(state, resp):
            break

    set_run_metadata(
        model=MODEL,
        steps=state.metadata["steps"],
        turns=state.metadata["turns"],
        stop_reason=state.stop_reason,
        tool_calls=len(state.metadata["tool_calls"]),
    )
    return state
```

## Project Layout

```md
anthropic-sdk/
├── cli.py                  `kata run`: builds the client, calls agent.main
├── agent.py                run(): the loop; main(): runs it and prints
├── state.py                AgentState: what the loop and handlers share
├── tracing.py              LangSmith: wrap the client, flush traces
├── style.py                terminal colours and errors
│
├── api/                    enums for the Messages API
│   ├── request.py          values you send (roles, block types)
│   └── response.py         values you receive (stop reasons, block types)
│
├── handlers/               one per stop_reason
│   ├── __init__.py         HANDLERS: stop_reason → handler
│   ├── tool_use.py         run the tools, send the results
│   ├── end_turn.py         take the final answer
│   ├── max_tokens.py       retry with more room (or stitch)
│   ├── pause_turn.py       API hasn't finished, send again as is
│   ├── stop_sequence.py    API generation stopped at stop_sequences
│   └── stop.py             refusal, context window full, unknown
│
├── tools/                  what the model can call
│   ├── __init__.py         TOOLS, SCHEMAS, run_tool
│   ├── base.py             @tool decorator
│   ├── schemas.py          pydantic Result, Card, Status
│   └── create_card, delete_card, find_card, get_card,
│       list_cards, schedule_card   (one .py each)
│
├── db/                     in-memory card store
│   ├── models.py           Card dataclass
│   ├── store.py            create, read, update, delete
│   ├── search.py           substring and fuzzy search
│   └── seed.py             the 3 sample cards
│
├── prompts/
│   ├── system.md           system prompt
│   └── max_tokens_merge.md "continue" message
│
├── evals/                  real model, scored in LangSmith
│   ├── run.py              target, dataset sync, experiment
│   ├── graders.py          the four graders
│   ├── judge.py            LLM judge
│   ├── config.py           .env and project name
│   └── cases/              create_card.py, delete_card.py
│
├── utils/
│   ├── utils.py            ToolError, prompts, max_tokens helpers
│   ├── agent.py            joins continued responses
│   └── log.py              debug logging
│
├── tests/                  no API key needed; mirrors the folders above
├── docs/                   cheatsheet, evals, system_prompt, tool_design
├── pyproject.toml, uv.lock dependencies and the `kata` command
└── .env.example            copy to .env (gitignored)
```