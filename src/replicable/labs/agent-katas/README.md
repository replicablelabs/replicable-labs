# agent-katas

Timed drills for the interview format: **improve an agent that uses tool use with the Anthropic API** in ~50 minutes, from starter
code: modify or create tools, write the logic behind them, adjust the prompting, and explain your trade-offs.
Raw `anthropic` SDK only: no frameworks, no databases, no Docker.

> **Run every command from this lab folder**, not the repo root. `uv run` uses the nearest `pyproject.toml`; at the repo root that is
> the *other* project, which has no `kata` command and fails with `Failed to spawn: kata ... No such file or directory`.
> From the repo root you can instead use `uv run --project src/replicable/labs/agent-katas kata ...`.

```bash
cd src/replicable/labs/agent-katas     # from the repo root: the lab folder, where all commands below must be run
uv sync
cp .env.example .env                   # katas 1-4 need no key; 5-6 call the model (see "Authentication")

# Your own code: src/katas/k0N_*/mine.py exists already (committed blank; git hides your edits automatically)
uv run kata list                       # progress
# just open src/katas/k01_loop/mine.py and write it
uv run kata test k01                   # run the tests against YOUR file; stops at the first failure (--all = show every failure)
uv run kata live k05 --runs 3          # katas 5-6: run YOUR file against the real model (--verbose shows tool calls)
uv run kata diff k01                   # your file vs the reference: look AFTER your attempt
uv run kata reset k01 --force          # wipe your file back to blank (--from starter = the buggy version to fix)
```
The `mine.py` files are committed blank; `kata` marks them `skip-worktree`, so your edits never appear in `git status` and `git add -A` never stages them (if you ever want to commit your work: `git update-index --no-skip-worktree <file>`). `kata reset` refuses to wipe a changed file without `--force`. Katas 5-6 start as a copy of the starter: you edit that.
Maintainer checks (not for practice): `uv run pytest -q` (starters fail on purpose) and `KATA_IMPL=solution uv run pytest -q`.

**Authentication (katas 5-6).** Either set `ANTHROPIC_API_KEY` in `.env`, or sign in with the `ant` CLI using an *inference* scope
(`ant auth login --profile dev --scope "user:inference"`, then `export ANTHROPIC_PROFILE=dev`). The default `ant` login only has
`org:admin`, which the API rejects for inference.

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
The live graders and plumbing are unit-tested offline (`tests/test_live_graders.py`). Measured on 2026-11-18 with `claude-sonnet-5-5`
(3 runs per case, so expect some variance):

| Kata | starter | reference solution | What separates them |
|---|---|---|---|
| 5 descriptions | 15/18 | 18/18 | `ORD-1001`: only a parameter description saying "strip the prefix" avoids a failed first call |
| 6 system prompt | 13/21 | 21/21 | company-specific rules a model cannot guess: refunds over $100 need human approval; one refund per order. Also: ask when the order id is missing (flaky on the starter) |

Honest note: a strong model already handles the *obvious* cases with weak descriptions/prompts (I first built easier cases and the
starters passed 100%, which taught nothing), so the cases target what only your wording can provide. In kata 6 the refund tool is
deliberately permissive (it checks only that the order exists and the amount is positive), so policy must live in the prompt; in
real systems you would also enforce the hard rules in code (kata 3). Be ready to discuss exactly that trade-off.

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

## Troubleshooting
- `error: Failed to spawn: kata ... No such file or directory`: you are not in the lab folder (see the note at the top). `cd` into
  `src/replicable/labs/agent-katas` and rerun. A stray `.venv` that uv created in the repo root is harmless (gitignored) and can be deleted.
- `403 ... OAuth token does not meet scope requirement`: your `ant` sign-in has no inference scope (see "Authentication").
