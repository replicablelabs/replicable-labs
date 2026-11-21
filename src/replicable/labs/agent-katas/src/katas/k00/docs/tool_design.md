# Tool design best practices

Notes from the k00 exercise. Tools are the agent's hands: the model only knows what each tool's schema and description tell it.

1. **Name and describe tools for the model.** The description is how Claude decides whether to call a tool. Say what the tool does, when to use it, and when not to. Example: "Use to fetch one card by its ID. To search by title, use list_cards instead."

2. **Keep each tool to one job.** Separate tools such as `get_card`, `list_cards`, and `create_card` are clearer than one `cards` tool with an `action` argument. Overlapping tools make the model guess.

3. **Use a strict schema.** Mark required fields, set types, and use `enum` for fixed choices. Set `additionalProperties: false`, and consider `strict: true` so arguments match the schema.

4. **Only list in `required` what must always be sent.** If a tool can be called by ID or by title, `required` must not force either one. Give both a default, say "provide at least one" in the description, and return an error result if neither arrives. (JSON Schema's `anyOf` can express "at least one of these", but I haven't checked that the API accepts it at the top level of `input_schema`.)

5. **Make parameters easy to fill correctly.** Prefer IDs that come from another tool's results over free-text guesses. Give parameters descriptive names and short descriptions.

6. **Keep schema, description and implementation in sync.** Best is to generate the first two from the code (see "Defining tools from docstrings" below). Then check that property names match the function's parameters, that every property named in `required` exists, and that the description doesn't promise behaviour the code doesn't have (for example, an error where the code returns `None`).

7. **Return what the model needs, and nothing more.** Return compact, relevant fields, including the IDs needed for the next call. Full database rows waste tokens and can distract.

8. **Report errors as results, not exceptions.** Wrap tool calls in the loop, so an exception becomes a `tool_result` with `is_error: true` and a message that says what went wrong and what to try next. The loop keeps running.

9. **Treat "not found" as a normal answer.** An empty or `None` lookup is a valid result, not a failure. Save `is_error` for real failures such as bad arguments or crashes.

10. **Answer every tool call.** If the model asks for several tools at once, return a result for each one, errors included. A missing result causes an API error on the next request.

11. **Make reads safe and writes deliberate.** Read tools should have no side effects. For writes, consider whether a retry could create duplicates.

12. **Keep the tool count small.** A few well-named tools work better than dozens, since each one adds to every request. Once the list grows, look at routers and lazy loading.

13. **Test with a prompt set.** Write 5 to 10 requests that should trigger each tool, plus some that shouldn't. Record the tool called, the arguments, and the final answer. Rerun after every change to descriptions or schemas.

14. **DO NOT** include output format. Output format is for the end user, and that is specified at the [system prompt]. This is about how the final reply looks, not about what a tool returns: document the tool's result shape (item 15).

15. **Specify each tool's input and output contract.** The API only has a schema for inputs; a tool's result is a plain string that the model reads. So describe the result in the description: the possible `status` values and their fields, what an empty result means, and what each status should make the model do next (for example, `exists` means ask the user, then call again with `replace`). Use the same result shape across tools so the model learns it once. Enforce that in code: tools return pydantic models from one `tools/schemas.py` (statuses in a single `Status` enum), and a wrapper serialises them. The model only ever sees the JSON, so the contract still has to reach it through the descriptions.

16. **Don't repeat result statuses in the system prompt.** The prompt says what the user should see ("ask before replacing a card"); the tool description says which status triggers it. Then renaming a status can't silently break the prompt. Recheck both whenever either changes.

17. **Return an object, even for a list.** Wrap lists as `{"cards": [...]}`, not a bare `[...]`. Every tool returns one `Result` (`status`, `cards`, `message`), where `cards` is always a list of zero, one or more cards, so every result has the same shape, an empty result is explicit (`{"cards": []}`), and you can add `total` or `truncated` later without changing the contract.

## Repo layout

```
k00/
  agent.py              entry point: `uv run kata run k00 "prompt"`; passes SCHEMAS to messages.create
  prompts/system.md    system prompt (policy: roles, rules, user-facing output format)
  tools/
    __init__.py        registry: TOOLS, SCHEMAS, run_tool(name, input) -> (content, is_error)
    base.py            @tool: @beta_tool plus serialising the returned result model to JSON
    schemas.py         pydantic contract for tool results: Status enum, Card, Result (one shape for every tool)
    <tool>.py          one module per tool (get_card.py, ...) with one @tool function; its docstring IS the tool definition
  db/                  in-memory card store: models (storage types), store, search, seed
                       (`tools/schemas.py` = what the model sees; `db/models.py` = what is stored)
  utils/utils.py       ToolError, show(), get_system_prompt()
  docs/                these notes: tool design, system prompt checklist, evals
```

Tests live outside this folder, in the lab's `tests/test_k00.py` (run `uv run pytest tests/test_k00.py` from `src/replicable/labs/agent-katas`): db behaviour, tool results, and a check that each definition matches its signature and docstring.

## Defining tools from docstrings (`@beta_tool`)

One decorated function per tool gives a single source of truth: the name, description and input schema are generated from it. These are the findings for `anthropic` 2.10.0.

| Part of the function | Reaches the model? | Becomes |
|---|---|---|
| Function name | yes | `name` |
| Docstring summary line | yes | start of `description` |
| Docstring body before the first section (paragraphs, bullets, `Note:`, `Warning:`) | yes | rest of `description` |
| `Args:` entries | yes | each property's `description` |
| Type hints and defaults | yes | property types, `default`, and `required` (parameters without a default) |
| `Returns:`, `Raises:`, `Example(s):`, `See Also:` | no | dropped by the decorator |
| Return annotation (`-> str`) | no | ignored |

Practical rules:

- Put everything the model needs (when to use it, input rules, results, errors, example calls) in the body, before `Args:`. Use `Returns:` and `Raises:` only as notes for developers.
- `@beta_tool` needs the function to return a string (or content blocks). Here `@tool` (in `tools/base.py`) wraps it: tools return a result model and the wrapper serialises it with `model_dump_json(exclude_none=True)`. The schema and description are still generated from the original function.
- `@beta_tool(description=...)` overrides the docstring if you ever need to keep the text elsewhere.
- Give optional parameters a default (`str = ""`), so Claude can leave them out. Avoid `str | None`, which adds an `anyOf` with `null`.
- Run the tool with `tool.call(input_dict)`: it validates arguments and raises `ValueError` if they are wrong. `tool.to_dict()` is the definition to send.
- Tests worth keeping: every parameter has an `Args:` entry, the required list matches the signature, every status a tool returns appears in its description, and every status in the `Status` enum is documented by some tool.