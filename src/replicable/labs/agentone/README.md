# agentone

An agent that makes **knowledge cards** (question + answer) and lets you **study** and **exercise** them.
Built to be re-coded by hand: LangGraph router/session, pydantic contracts, per-card embeddings *and* a
knowledge graph, hybrid retrieval, LLM-judge scoring, offline evals. All local (no Docker).

```bash
cd src/replicable/labs/agentone       # from the repo root
uv sync && uv run pytest -q           # 18 tests, no API key (scripted fake LLM + hash embedder)

cp .env.example .env                  # then fill in ANTHROPIC_API_KEY / OPENAI_API_KEY / LANGSMITH_API_KEY (gitignored)
# (exported shell vars override .env; use --provider openai to run on OpenAI)
alias cards="uv run python -m agentone.cards.cli"
cards seed                            # 8-card demo deck (pre-extracted triples, no LLM needed)
cards add "What is X?" "X is ..."     # embeds the card + LLM-extracts triples -> graph
cards study                           # or: cards study --card c3
cards exercise                        # picks never-attempted, then weakest cards
cards list; cards graph; cards eval   # eval = retrieval recall@3 (vector vs graph vs hybrid), offline
# --provider openai   --embedder openai   (Claude has no embeddings API; default embedder is offline `hash`)
```
Cards persist in `data/cards.local.json` (gitignored; override with `--db` / `AGENTONE_DB`).

## Study vs exercise

| | **Study** | **Exercise** |
|---|---|---|
| Learner sees | question **and** answer | question only |
| Tutor knows the answer | yes | **no** (structurally not in its prompt; current card's vector + graph edges excluded from retrieval; output leak-guard as backup) |
| Learner can | ask questions; `/card` (or "make that a card") creates a new card, linked `prerequisite_of` the current one, embedded + graph-ingested | ask for hints; `/answer ...` submits the final answer |
| End of turn | tutor reply | LLM judge → pydantic `Score` (0-1, verdict, feedback) saved as an `Attempt`; answer revealed after |

**Router** (`cards/session.py`): `/answer`, `/card` slash-commands route deterministically; otherwise an LLM classifies
into `ask | create_card | submit_answer` (pydantic `RouteDecision`); then a hard per-mode guard coerces disallowed
intents to `ask`. So exercise mode cannot create cards or leak, whatever the model says.

## Where each concept lives (`src/agentone/cards/`)

| File | Concept |
|---|---|
| `models.py` | **pydantic**: `Card, Triple, CardExtraction, DraftCard, RouteDecision, Score, Attempt` (bounds → invalid judge output = retry) |
| `llm.py` | `LLM` protocol; Anthropic (forced tool call = schema output) and OpenAI (JSON mode) impls; validate + retry once |
| `embed.py` | embedders + cosine (`HashEmbedder` offline, `OpenAIEmbedder`) |
| `store.py` | **vector side**: card→embedding; **graph side**: card→triples; graph derived (nodes = entities, edges carry `card_id` provenance); attempts; scheduler |
| `ingest.py` | card → embed + extract triples + persist |
| `retrieve.py` | vector top-k + graph k-hop around entities named in the query, fused with reciprocal-rank fusion; `exclude` |
| `session.py` | **LangGraph** `StateGraph`: route → ask / create_card / score; checkpointer per `thread_id` |
| `evals.py` | retrieval recall@k (no key), router accuracy, judge accuracy (need an LLM) |
| `cli.py` | study/exercise REPLs |

Honest limits: entity linking is substring match; `HashEmbedder` is lexical, so the offline eval is easy and does not
show real semantic retrieval; no spaced-repetition scheduling beyond "weakest first".

## Foundations (earlier lab files, still here)
Raw agent loops `loop.py` (Anthropic) / `loop_openai.py`, `harnesses.py` (anthropic / openai / deepagents side by side),
`lg_agent.py`, `deep_agent.py`, `sdk_agent.py`, `graphrag.py`, `evals/offline.py|online.py` (LangSmith). Run
`uv run python -m agentone.harnesses`. Know `loop.py` cold; it is the likeliest interview exercise.

## Study plan
**Day 1** raw loop (rewrite `loop.py` from memory; wire formats for Anthropic vs OpenAI). **Day 2** cards data model:
rewrite `models.py`, `ingest.py`, `retrieve.py`; swap `HashEmbedder` for real embeddings, replace substring entity
linking, add community summaries. **Day 3** rebuild `session.py` from scratch (state, reducer, conditional edges,
checkpointer; add `interrupt_before` human approval before card creation). **Day 4** evals: extend `evals.py`
(router/judge on real labels, LangSmith `evaluate`, `@traceable` online feedback). **Day 5** timed mock: "build an
agent that does X over a document set with tools" from an empty file.

Proxy: Anthropic SDK honours `ANTHROPIC_BASE_URL`, OpenAI SDK `OPENAI_BASE_URL`. LangSmith:
`LANGSMITH_TRACING=true LANGSMITH_API_KEY=... LANGSMITH_PROJECT=agentone`.
