# Agentic coding superuser lab

A hands-on lab for getting the most out of Claude Code on a real codebase
(this repository). It runs on your machine, not in Docker, so Claude uses your
own login, your real files and your terminal.

The lab has no code of its own. It loads the
[`replicable-harness`](https://github.com/replicablelabs/replicable-claude)
Claude Code plugin at the version pinned in [`lab.json`](lab.json), which
builds on [graphify](https://github.com/Graphify-Labs/graphify)'s code graph:

| Piece | What it does | Provided by |
| --- | --- | --- |
| Code graph and queries | `graphify update`, `query`, `explain`, `path`, `affected` | graphify |
| Edit → verify hook | After each edit: re-index, then "can affect N symbols; tests to run: …" | plugin |
| Test gate | Opt-in Stop hook: Claude can't end a turn while the tests are red (3 retries) | plugin |
| Project wiki | `wiki/`: decisions, domain rules and traps, checked in CI; hooks flag pages an edit may have made wrong | plugin |
| Subagents | `graph-explorer`, `reviewer` | plugin |
| Skills | `setup`, `epcc`, `tdd`, `test-gate`, `headless-loop`, `wiki-ingest`, `wiki-lint` | plugin |

## Start

You need the [Claude Code CLI](https://docs.claude.com/claude-code) (signed in
with your own account), `git`, and graphify:

```bash
uv tool install "graphifyy[mcp]"   # or: pipx install graphifyy
source .venv/bin/activate
python -m pip install -e .          # once, if you have not already
replicable labs start agentic-coding-superuser
# pass flags to claude after --:
replicable labs start agentic-coding-superuser -- --model opus --permission-mode plan
```

The launcher clones the plugin at the pinned tag into `.data/plugins/` (once;
it is gitignored) and runs `claude --plugin-dir <that clone>` from the
repository root. To try a local checkout of the plugin instead, set
`REPLICABLE_HARNESS_DIR=~/path/to/replicable-claude`.

You can also install the plugin permanently instead of using the launcher:

```text
/plugin marketplace add replicablelabs/replicable-claude
/plugin install replicable-harness@replicablelabs
```

The first session builds the graph. Run `/replicable-harness:setup` once: it
installs graphify's Claude Code rules and sets up the wiki (it shows a diff and
asks first). Plugin skills are namespaced: type `/replicable-harness:` to list
them.

## Exercises

Each exercise practises one habit. Do them in order the first time.

### 1. Context: query the graph instead of grepping

- Ask: *"What breaks if I change `_load_env`, and which tests should I run?"*
  Watch Claude use `graphify affected` instead of reading whole files.
- Ask: *"How does `replicable labs start` end up calling `ChatGPTSession`?"*
  (`graphify path`).
- Compare with a session started without the plugin: count the tool calls and
  the files read. Use `/context` to see how much of the window you used.

### 2. Subagents keep exploration out of your context

- *"Use the graph-explorer agent to find everything that touches LangSmith
  configuration."* The subagent reads in its own context and returns only the
  answer. Run two in parallel on independent questions.

### 3. Hooks: the edit → verify loop

- Ask for a small change in `src/replicable/cli.py`. After the edit, the
  PostToolUse hook adds the blast radius and "Tests to run: tests/test_cli.py".
  Check that Claude runs them.
- `/replicable-harness:test-gate on`, then ask for a change that breaks a
  test. The Stop hook sends Claude back with the failure, up to 3 times.
  `/replicable-harness:test-gate off` turns it off.

### 4. The wiki: intent the code can't tell you

- After `/replicable-harness:setup`, ask *"Record in the wiki why the lab
  launcher runs Claude Code on the host instead of in Docker"*
  (`wiki-ingest`). Read the page it creates in `wiki/`, in Obsidian or on
  GitHub.
- Edit a file the page lists under `code`. The edit hook names the page;
  start a new session and the reminder brings it up again until the page is
  updated. `/replicable-harness:wiki-lint` verifies it against the code.

### 5. Workflows and loops

- **Explore → Plan → Code → Commit:** `/replicable-harness:epcc add a
  --dry-run flag to replicable labs start`, in plan mode (Shift+Tab).
- **Test-driven development:** `/replicable-harness:tdd <behaviour>`.
- **Writer / reviewer:** a writer session in its own worktree (`claude -w
  feature-x`), then a fresh session: *"Use the reviewer agent on branch
  worktree-feature-x"*.
- **`/loop` and `/schedule`:** run a check on a timer in the session, or in the
  cloud while your laptop is closed.
- **Headless "Ralph" loop:** `/replicable-harness:headless-loop` runs fresh
  `claude -p` processes in their own worktree until the tests pass and the
  agent says it is done, with iteration and budget caps.

### 6. See what it costs

`/cost`, `/context`, and `claude plugin details replicable-harness` for the
tokens the plugin adds to every session.

## Tests

```bash
python -m unittest tests.test_agentic_lab -v
```

They cover the launcher: the pinned clone, the local-checkout override, and
the errors when `claude` or `git` is missing. The plugin's own tests live in
its repository.
