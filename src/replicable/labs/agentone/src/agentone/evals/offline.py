"""OFFLINE evals: fixed dataset + evaluators, run before shipping (CI / experiments).
Three evaluator kinds to be able to explain: code (exact), trajectory (tool use), LLM-as-judge.
`run_local` needs no network; `run_langsmith` uploads an experiment to LangSmith (needs LANGSMITH_API_KEY)."""
from __future__ import annotations
from agentone import graphrag
from agentone.loop import run_agent

def dataset() -> list[dict]:
    return graphrag.load()["qa"]

# --- evaluators: (example, result) -> {"key","score"} ---
def correct(ex, res) -> dict:
    key = ex["a"].lower().split()[0]
    return {"key": "correct", "score": float(key in res.answer.lower())}

def used_enough_hops(ex, res) -> dict:  # trajectory eval: did it search at least `hops` times?
    n = sum(1 for name, _ in res.tool_calls if name == "graph_search")
    return {"key": "enough_searches", "score": float(n >= ex["hops"])}

def efficient(ex, res) -> dict:
    return {"key": "efficient", "score": float(res.steps <= ex["hops"] + 2)}

def llm_judge(ex, res, client=None, model="claude-haiku-5-5") -> dict:
    """LLM-as-judge: pin the rubric, force a parseable verdict, temperature 0, validate the judge on a few labels."""
    import anthropic
    client = client or anthropic.Anthropic()
    r = client.messages.create(model=model, max_tokens=5, temperature=0, messages=[{"role": "user", "content":
        f"Question: {ex['q']}\nReference: {ex['a']}\nAnswer: {res.answer}\nIs the answer consistent with the reference? Reply only YES or NO."}])
    return {"key": "judge", "score": float(r.content[0].text.strip().upper().startswith("YES"))}

EVALUATORS = [correct, used_enough_hops, efficient]

def run_local(agent=run_agent, evaluators=EVALUATORS) -> dict[str, float]:
    scores: dict[str, list[float]] = {}
    for ex in dataset():
        res = agent(ex["q"])
        for ev in evaluators:
            o = ev(ex, res); scores.setdefault(o["key"], []).append(o["score"])
    return {k: sum(v) / len(v) for k, v in scores.items()}

def run_langsmith(name="agentone-offline"):
    from langsmith import Client, evaluate
    c = Client()
    if not c.has_dataset(dataset_name=name):
        ds = c.create_dataset(name)
        c.create_examples(dataset_id=ds.id, examples=[{"inputs": {"q": e["q"]}, "outputs": e} for e in dataset()])
    def target(inputs): 
        r = run_agent(inputs["q"]); return {"answer": r.answer, "tool_calls": r.tool_calls, "steps": r.steps}
    def wrap(ev):
        def f(run, example):
            from types import SimpleNamespace as NS
            return ev(example.outputs, NS(answer=run.outputs["answer"], tool_calls=run.outputs["tool_calls"], steps=run.outputs["steps"]))
        f.__name__ = ev.__name__; return f
    return evaluate(target, data=name, evaluators=[wrap(e) for e in EVALUATORS], experiment_prefix="agentone")

if __name__ == "__main__":
    print(run_local())
