# agent-katas

Timed drills for the interview format: **improve an agent that uses tool use with the Anthropic API** in ~50 minutes, from starter
code: modify or create tools, write the logic behind them, adjust the prompting, and explain your trade-offs.
Raw `anthropic` SDK only: no frameworks, no databases, no Docker.

```bash
cd src/replicable/labs/agent-katas     # from the repo root
uv sync
uv run pytest -q                       # starters: the planted bugs FAIL (that is the exercise)
KATA_IMPL=solution uv run pytest -q    # reference solutions: everything passes (peek only after your attempt)
cp ../agentone/.env.example .env       # then set ANTHROPIC_API_KEY (only the live katas need it)
```

## Katas (do in order; ~10-15 min each, then explain out loud)

| # | Kata | You edit | Checked by | Core ideas |
|---|---|---|---|---|
| 1 | **The loop** `k01_loop/starter.py` | the loop | tests (strict fake client that rejects malformed messages like the real API) | assistant content kept verbatim incl. `tool_use`; ALL results in ONE user message; `is_error` instead of crashing; `max_steps`; `stop_reason` |
| 2 | **Tool output** `k02_tool_output` | `lookup_order` | tests | return what the model needs, nothing it must not see (PII/internal), bound the size, say how to get more, actionable not-found |
| 3 | **Tool logic + errors** `k03_tool_errors` | `issue_refund` | tests | validate inputs, enforce business rules in code, errors that say what is wrong AND what is valid, no side effects on failure |
| 4 | **Structured output** `k04_structured_output` | `classify_ticket` | tests | forced `tool_choice` + JSON-schema enums; validate; feed errors back as `tool_result` `is_error` and retry once |
| 5 | **Tool descriptions** `k05_descriptions` | `SCHEMAS` | **live** model | when to use / when NOT to use, formats, preconditions, overlapping tools |
| 6 | **System prompt** `k06_system_prompt` | `SYSTEM` | **live** model | policy in prompt vs in code, verify-before-act, ask when info is missing, no retry loops |

Katas 1-4 are deterministic: run `uv run pytest tests/test_k0N.py`. Katas 5-6 need the real model (non-deterministic, so use `--runs`):
```bash
uv run python -m katas.live k05_descriptions --runs 3 --verbose
uv run python -m katas.live k06_system_prompt --runs 3
uv run python -m katas.live k06_system_prompt --impl solution --runs 3     # compare with the reference
```
The live graders and plumbing are unit-tested offline (`tests/test_live_graders.py`), but **no live run has been done yet**: the
first real run may show that a case or a reference prompt needs tuning. Treat failures there as data, not as gospel.

## Practice protocol
1. Timer 12 min per kata. Read failing tests/traces first, change the smallest thing, re-run.
2. Say your reasoning aloud as you go (the interview scores discussion too): *what failed, why, what else could I have changed, what does it cost?*
3. After each kata answer: how would I know the change helped (test, eval set, trajectory check, production logging)?

## Trade-off prompts to rehearse
- Rule in the prompt vs enforced in tool code? (Both; code is the guarantee, prompt saves wasted calls.)
- One flexible tool vs several narrow ones? Tool names/descriptions vs system prompt for steering?
- Tool errors: raise, return a string, or `is_error`? What should an error message contain?
- Output size: truncate, paginate, summarise? Where does the model learn how to get more?
- Parallel tool calls: when safe? Idempotency and irreversible actions (refunds)?
- Retry policy: who retries (loop, tool, model)? How do you avoid retry storms?
- Evals for agents: outcome vs trajectory checks, flakiness (`--runs`), regression sets.

## Layout
`src/katas/{world,fakes,world_tools,cases,live,loader}.py` shared pieces; `k0N_*/starter.py` (yours) and `solution.py` (reference);
`tests/` per kata. `KATA_IMPL=starter|solution` picks which implementation tests/live runner load.
