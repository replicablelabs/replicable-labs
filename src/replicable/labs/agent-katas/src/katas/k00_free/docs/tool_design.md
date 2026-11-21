# Tool design best practices

Notes from the k00 exercise. Tools are the agent's hands: the model only knows what each tool's schema and description tell it.

1. **Name and describe tools for the model.** The description is how Claude decides whether to call a tool. Say what the tool does, when to use it, and when not to. Example: "Use to fetch one card by its ID. To search by title, use list_cards instead."

2. **Keep each tool to one job.** Separate tools such as `get_card`, `list_cards`, and `create_card` are clearer than one `cards` tool with an `action` argument. Overlapping tools make the model guess.

3. **Use a strict schema.** Mark required fields, set types, and use `enum` for fixed choices. Set `additionalProperties: false`, and consider `strict: true` so arguments match the schema.

4. **Only list in `required` what must always be sent.** If a tool can be called by ID or by title, `required` must not force either one. Use `anyOf` to say "at least one of these."

5. **Make parameters easy to fill correctly.** Prefer IDs that come from another tool's results over free-text guesses. Give parameters descriptive names and short descriptions.

6. **Keep schema, description and implementation in sync.** Check that property names match the function's parameters, that every property named in `required` exists, and that the description doesn't promise behaviour the code doesn't have (for example, an error where the code returns `None`).

7. **Return what the model needs, and nothing more.** Return compact, relevant fields, including the IDs needed for the next call. Full database rows waste tokens and can distract.

8. **Report errors as results, not exceptions.** Wrap tool calls in the loop, so an exception becomes a `tool_result` with `is_error: true` and a message that says what went wrong and what to try next. The loop keeps running.

9. **Treat "not found" as a normal answer.** An empty or `None` lookup is a valid result, not a failure. Save `is_error` for real failures such as bad arguments or crashes.

10. **Answer every tool call.** If the model asks for several tools at once, return a result for each one, errors included. A missing result causes an API error on the next request.

11. **Make reads safe and writes deliberate.** Read tools should have no side effects. For writes, consider whether a retry could create duplicates.

12. **Keep the tool count small.** A few well-named tools work better than dozens, since each one adds to every request. Once the list grows, look at routers and lazy loading.

13. **Test with a prompt set.** Write 5 to 10 requests that should trigger each tool, plus some that shouldn't. Record the tool called, the arguments, and the final answer. Rerun after every change to descriptions or schemas.

14. **DO NOT** include output format. Output format is for the end user, and that is specified at the [system prompt]