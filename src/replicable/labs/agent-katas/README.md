# agent-katas

Timed drills for the interview format: **improve an agent that uses tool use with the Anthropic API** in ~50 minutes, starting
from provided code: modify or create tools, write the logic behind them, adjust the prompting, and explain your trade-offs.
Raw `anthropic` SDK only: no frameworks, no databases, no Docker.

> **Run every command from this lab folder**, not the repo root. `uv run` uses the nearest `pyproject.toml`; at the repo root that is
> the *other* project, which has no `kata` command and fails with `Failed to spawn: kata ... No such file or directory`.
> From the repo root you can instead use `uv run --project src/replicable/labs/agent-katas kata ...`.

## Setup

```bash
cd src/replicable/labs/agent-katas     # from the repo root
uv sync
cp .env.example .env                   # the tests (katas 1-4) need no key; `kata run` and `kata live` call the model (see Authentication)
uv run kata list                       # all six katas should show "blank / not started"
```

**Authentication (only for commands that call the model: `kata live` on katas 5-6, and `kata run` on katas 1, 4, 5, 6).** Either set `ANTHROPIC_API_KEY` in `.env`, or sign in with the `ant` CLI
using an *inference* scope and select that profile:
```bash
ant auth login --profile dev --scope "user:inference"
export ANTHROPIC_PROFILE=dev           # per terminal
```
The default `ant` login only has `org:admin`, which the API rejects for inference (`403 ... OAuth token does not meet scope requirement`).

## The six katas

Each kata isolates one skill. Do them in order, ~12 minutes each, and explain your reasoning out loud.

| # | Kata | Edit | Checked by | Core ideas |
|---|---|---|---|---|
| 1 | **The loop** `k01_loop` | `run_agent` | tests (strict fake client that rejects malformed messages like the real API) | assistant content kept verbatim incl. `tool_use`; ALL results in ONE user message; `is_error` instead of crashing; `max_steps`; `stop_reason` |
| 2 | **Tool output** `k02_tool_output` | `lookup_order` | tests | return what the model needs, nothing it must not see (PII/internal), bound the size, say how to get more, derive values the model can't (days since delivery), actionable not-found |
| 3 | **Tool logic + errors** `k03_tool_errors` | `issue_refund` | tests | validate inputs, enforce business rules in code, errors that say what is wrong AND what is valid, no side effects on failure |
| 4 | **Structured output** `k04_structured_output` | `classify_ticket` | tests | forced `tool_choice` + JSON-schema enums; validate; feed errors back as `tool_result` `is_error` and retry once |
| 5 | **Tool descriptions** `k05_descriptions` | `SCHEMAS` | **live model** | when to use / when NOT to use, argument formats, preconditions, overlapping tools |
| 6 | **System prompt** `k06_system_prompt` | `SYSTEM` | **live model** | policy in prompt vs in code, verify-before-act, ask when info is missing, no retry loops |

## How to practise: two modes per kata

Every kata has two files of yours. Both are committed pristine, and **git ignores your edits to them** (see "Files and git" below).

| Mode | File you edit | Starts as | Use it to |
|---|---|---|---|
| **Write from scratch** | `src/katas/k0N_*/mine.py` | a skeleton: signature + contract, body raises `NotImplementedError` | build it yourself |
| **Fix the existing code** | `src/katas/k0N_*/starter.py` | a working-looking implementation with planted bugs | debug it, as in the interview |

For katas 5-6 there is no blank form: `mine.py` starts as a copy of the starter (you edit the descriptions / the prompt).

## Commands

```bash
uv run kata list                       # progress on all six
uv run kata test k01                   # run the tests against YOUR mine.py; stops at the FIRST failure (--all shows every failure)
uv run kata test k01 --starter         # ... against the buggy starter.py you are fixing
uv run kata test k01 --solution        # ... against the reference (what passing looks like)
uv run kata run k01 "Where is order #1002?"   # actually RUN the code (no tests) and watch each step; same --starter / --solution flags
uv run kata live k05 --runs 3          # katas 5-6: score your file against the real model (--verbose prints the tool calls)
uv run kata diff k01                   # your mine.py vs the reference: look AFTER your attempt
uv run kata reset k01 --force          # wipe mine.py back to blank (--from starter | solution)
uv run kata reset k01 --target starter --force   # restore the buggy starter.py after you fixed it, to redo it
```
Every command prints the file it used, e.g. `[running k01_loop/mine.py]`. `kata reset` refuses to wipe a file you changed unless you pass `--force`.

**The loop to follow:** edit the file, `kata test kNN`, read the one failure, fix that one thing, repeat; when green run `kata test kNN --all` once.

### Run the code for real (`kata run`)
```bash
uv run kata run k01 "Where is order #1002?"        # your loop vs the real model with the shop tools; prints every tool call and result
uv run kata run k02 1005                           # what lookup_order returns (what the model would read)
uv run kata run k03 1001 10                        # issue_refund(order, amount): result + refunds recorded
uv run kata run k04 "I was charged twice"          # classify a ticket with the real model
uv run kata run k05 "Status of ORD-1001"           # an agent using YOUR tool descriptions
uv run kata run k06 "Refund order 1005 for $200"   # an agent using YOUR system prompt
```
Katas 2 and 3 are offline; 1, 4, 5, 6 call the real model. Running the buggy starter often shows the bug directly (e.g. `k03 --starter` with an
unknown order crashes instead of returning an error the model can use).

## Live katas (5 and 6): measured baselines

The live graders and plumbing are unit-tested offline (`tests/test_live_graders.py`). Measured on 2026-11-18 with `claude-sonnet-5-5`,
3 runs per case (expect some variance):

| Kata | starter | reference solution | What separates them |
|---|---|---|---|
| 5 descriptions | 15/18 | 18/18 | `ORD-1001`: only a parameter description saying "strip the prefix" avoids a failed first call |
| 6 system prompt | 13/21 | 21/21 | company-specific rules a model cannot guess: refunds over $100 need human approval; one refund per order. Also: ask when the order id is missing (flaky on the starter) |

Honest note: a strong model already handles the *obvious* cases with weak descriptions/prompts (my first, easier cases passed 100% on the
starters and taught nothing), so the cases target what only your wording can provide. In kata 6 the refund tool is deliberately permissive
(it checks only that the order exists and the amount is positive), so policy must live in the prompt; real systems also enforce hard rules
in code (kata 3). Be ready to discuss exactly that trade-off.

**API quirk worth knowing (found by running it):** `tool_choice` of type `"tool"` or `"any"` (forcing a tool call) is rejected with a 400 by
`claude-sonnet-5-5`, `claude-opus-5-5` and `claude-fable-5-2`; only `claude-haiku-5-5` accepts it. `"auto"` works everywhere. Kata 4's tests use
a fake client, so they cannot catch this; `kata run k04` therefore uses Haiku (override with `KATA_K04_MODEL`). With a model that refuses
forcing, the fallback is `auto` + a clear instruction to answer via the tool + the same validate-and-retry loop. Be ready to discuss it.

## Files and git

Per kata, in `src/katas/k0N_*/`:

| File | Role | Edited by | In git |
|---|---|---|---|
| `skeleton.py` | pristine blank template (katas 1-4) | nobody | tracked |
| `mine.py` | your from-scratch attempt | you | tracked pristine, **your edits hidden** |
| `starter.py` | the buggy code to fix | you | tracked pristine, **your edits hidden** |
| `solution.py` | reference solution (also used by the live katas and `--solution`) | nobody | tracked |

`kata` marks every `mine.py` and `starter.py` as `skip-worktree` (a local git setting, re-applied on every `kata` command, including after a
fresh clone). Your edits never show in `git status` and `git add -A` never stages them. To commit your own work on purpose:
`git update-index --no-skip-worktree <file>`. If the pristine file ever changes upstream, a `git pull` may complain about a hidden file:
run `uv run kata reset kNN --force` (and `--target starter`) first. `kata list` and the resets compare against the *committed* text, so editing a
starter can't confuse them.

## Practice protocol
1. Timer 12 min per kata. Read failing tests/traces first, change the smallest thing, re-run.
2. Say your reasoning aloud (the interview scores discussion too): *what failed, why, what else could I have changed, what does it cost?*
3. After each kata answer: how would I know the change helped (test, eval set, trajectory check, production logging)?
4. A day later, reset the kata and redo it from memory.

## Trade-off prompts to rehearse
- Rule in the prompt vs enforced in tool code? (Both; code is the guarantee, prompt saves wasted calls.)
- One flexible tool vs several narrow ones? Tool names/descriptions vs system prompt for steering?
- Tool errors: raise, return a string, or `is_error`? What should an error message contain?
- Output size: truncate, paginate, summarise? Where does the model learn how to get more?
- Parallel tool calls: when safe? Idempotency and irreversible actions (refunds)?
- Retry policy: who retries (loop, tool, model)? How do you avoid retry storms?
- Forcing structured output: forced `tool_choice` vs `auto` + instruction, and what to do when a model rejects forcing.
- Evals for agents: outcome vs trajectory checks, flakiness (`--runs`), regression sets.

## Layout (for maintainers)
`src/katas/{world,fakes,world_tools,cases,live,run,cli,loader}.py` are shared pieces (`fakes` = strict fake Anthropic client; `world` = the
deterministic shop; `cases` = live-kata graders); `k0N_*/` hold the per-kata files above; `tests/` has one file per kata plus
`test_live_graders.py`. `KATA_IMPL=mine|starter|solution` selects which file tests and the live runner load (`kata` sets it for you).
Maintainer checks (the starters fail on purpose): `uv run pytest -q` and `KATA_IMPL=solution uv run pytest -q`.

## Troubleshooting
- `error: Failed to spawn: kata ... No such file or directory`: you are not in the lab folder (see the note at the top). A stray `.venv` that
  uv created in the repo root is harmless (gitignored) and can be deleted.
- `403 ... OAuth token does not meet scope requirement`: your `ant` sign-in has no inference scope (see Authentication).
- VS Code shows `Import "katas.loader" could not be resolved`: select the lab's interpreter (Cmd+Shift+P, Python: Select Interpreter,
  `.../agent-katas/.venv/bin/python`) or open this lab folder as the workspace. It is cosmetic; `uv run` is unaffected.
- `400 ... tool_choice: type "tool" and "any" are not supported for this model`: see the API quirk above.
