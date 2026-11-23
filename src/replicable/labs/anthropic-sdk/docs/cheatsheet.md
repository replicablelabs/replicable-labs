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

**Loop shape**: send → read `stop_reason` → dispatch to handler → append assistant content and tool results → repeat, capped by `MAX_STEPS`.
