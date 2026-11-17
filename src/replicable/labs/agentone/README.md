# agentone

Learn to build an agent **by hand** in a few days: raw loop → LangGraph → deepagents → Agent SDK →
GraphRAG → offline/online evals (LangSmith). Everything runs against one tiny domain (a company knowledge
graph, `data/corpus.json`) with multi-hop questions, so each layer solves the *same* problem.

```bash
cd src/replicable/labs/agentone
uv sync
uv run pytest -q                      # no API key needed (fake client)
export ANTHROPIC_API_KEY=...          # for live runs
uv run python -m agentone.loop "Who leads the team that owns the Schema Registry?"
```

Proxy / Hugging Face: the Anthropic SDK reads `ANTHROPIC_BASE_URL`, so any Anthropic-compatible proxy works
with zero code change. For HF/OpenAI-style endpoints, swap the client in `loop.py` (the loop shape is identical;
only the tool-call message format differs: `tool_calls` + `role: "tool"` instead of `tool_use`/`tool_result` blocks).
LangSmith: `LANGSMITH_TRACING=true LANGSMITH_API_KEY=... LANGSMITH_PROJECT=agentone`.

## Three harnesses, same questions

```bash
export OPENAI_API_KEY=... ANTHROPIC_API_KEY=...
uv run python -m agentone.harnesses                       # all three
uv run python -m agentone.harnesses openai -- "Which team builds the Ingestion Pipeline?"
DEEPAGENTS_MODEL=openai:gpt-4.1 uv run python -m agentone.harnesses deepagents   # deepagents on OpenAI
```
`anthropic` = `loop.py`, `openai` = `loop_openai.py` (you own the loop in both; compare the wire formats),
`deepagents` = framework owns the loop. Prints answer / steps / tool calls / seconds per harness.
Only one key is needed per harness you run; missing-key errors are reported per row, not fatal.

## Map

| File | Concept |
|---|---|
| `src/agentone/loop.py` | **The interview file.** Raw Messages-API agent loop |
| `src/agentone/loop_openai.py` | Same loop on OpenAI Chat Completions (`tool_calls`, `role: tool`) |
| `src/agentone/harnesses.py` | Side-by-side runner: anthropic / openai / deepagents |
| `src/agentone/tools.py` | Tool schema + dispatch, errors returned to the model |
| `src/agentone/graphrag.py` | Triples → graph, entity linking, k-hop local search, communities |
| `src/agentone/lg_agent.py` | LangGraph: state, nodes, conditional edges, checkpointer |
| `src/agentone/deep_agent.py` | deepagents: todos, virtual FS, subagents |
| `src/agentone/sdk_agent.py` | Claude Agent SDK: in-process MCP tools, built-in loop |
| `src/agentone/evals/offline.py` | Dataset + code/trajectory/LLM-judge evaluators, LangSmith `evaluate` |
| `src/agentone/evals/online.py` | `@traceable`, sampling, reference-free scores, user feedback |

## Plan (adapt to your days)

**Day 1 — Raw loop (most important).** Read `loop.py`, then *delete it and rewrite from memory* until you can in
~15 min. Must-know: `stop_reason == "tool_use"`; append the assistant `content` verbatim; ALL tool results for one
turn go in ONE user message, each with matching `tool_use_id`; `is_error`; `max_steps` guard; system prompt separate.
Then extend by hand: parallel tool calls, streaming, token/cost tracking, prompt caching, a 3rd tool,
context trimming, retries on 429/overloaded. Write tests with `tests/fakes.py`.

**Day 2 — GraphRAG.** Why graph beats vector for multi-hop (relationships live in edges, not chunks). Rewrite
`graphrag.py`: build graph, link entities, k-hop retrieval. Extend: LLM triple extraction (JSON output, validate),
embedding-based entity linking, hybrid (vector seed + graph expand), community summaries for global questions.
Know the tradeoffs: indexing cost, extraction errors, hop explosion (cap hops / prune by relation).

**Day 3 — LangGraph + deepagents.** Rebuild the loop as `StateGraph` (`lg_agent.py`). Add: checkpointer + `thread_id`
memory, `interrupt_before=["tools"]` human approval, a custom reducer, a router node. Then `deep_agent.py`: what
middleware adds (planning, filesystem, subagents, summarisation) and when that is overkill.

**Day 4 — Agent SDK + evals.** `sdk_agent.py` (custom tools via MCP server, `allowed_tools`, hooks, permissions).
Offline: run `python -m agentone.evals.offline`; break the agent on purpose and watch scores fall; add a failing
case, fix, re-run (regression loop). Online: trace, sample, reference-free metrics, feedback, dashboards/alerts.
Be ready to discuss judge bias/validation, dataset construction, flaky tests (`num_repetitions`), trajectory vs outcome.

**Day 5 — Mock interviews.** 45 min timer: "build an agent that answers questions over X with tools Y" from an empty
file; then "here is a buggy agent — fix it" (try: result sent as separate messages, dropped `tool_use_id`, no max-step).

## Interview talking points
- Agent = LLM + tools + loop + stopping condition; everything else is context management and reliability.
- Failure modes: infinite loops, tool errors, context blowup, hallucinated tool args, prompt injection via tool output.
- Evals first: define success, build 20 good cases, trajectory + outcome, then iterate.
