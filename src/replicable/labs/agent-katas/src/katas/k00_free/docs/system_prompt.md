# System prompt checklist

The system prompt holds **policy** (rules that span tools). Tool `description.md` files hold **mechanics** (what each tool does, when to use it). Prompt and tools are one contract.

## Write it (what goes in `prompts/system.md`)

| Do this | Tag |
|---|---|
| State who the agent serves and what it is for, in 1-2 sentences. No definitions here. | `<role>` |
| Give facts the model needs: terms. | `<context>` |
| Say what to do, in parallel imperative steps ("Look up the card before answering"). | `<instructions>` |
| A rule belongs in the prompt only if the model would otherwise get it wrong. | `<rules>` |
| Add a `because` to each rule so it generalises. | `<rules>` |
| Say how replies should look. | `<output_format>` |
| Show 3-5 input/output pairs only when a case can't be explained in words. | `<examples>` |

## Keep it clean

- Every sentence has one reading. Fix typos and fragments.
- No overlapping or conflicting rules. Delete a rule that changes no eval result.
- Plain wording. No capitals or "NEVER" unless a test shows you need them.
- Fixed text first. No timestamps or user names (they break prompt caching).
- Don't promise what the tools can't do.
- In output templates, mark placeholders visibly (`[title]`, `[score]`), not as plain words the model may copy literally.

## Maintain it (stays out of the prompt)

1. Write an eval case for the behaviour first.
2. Change one thing, rerun the cases, keep it only if results improve.
3. Add a rule only after a case fails. Ask first: is the wording unclear, or is the tool description missing something?
4. When you change a tool or the model, recheck the prompt too, and version both together.

## Sources

- Anthropic, [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices): role, reasons behind rules, XML tags, examples, the colleague test.
- Unsourced, treat as judgment: plain wording (no capitals), no contradictions, visible placeholders in templates, policy vs. mechanics, versioning prompt and tools together.
- Prompt-caching order comes from the claude-api skill's prompt-caching guide, not the page above.
