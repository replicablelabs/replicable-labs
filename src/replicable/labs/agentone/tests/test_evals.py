from agentone.evals import offline
from agentone.loop import Result

def perfect(q):
    ex = next(e for e in offline.dataset() if e["q"] == q)
    return Result(ex["a"], [], ex["hops"], [("graph_search", {})] * ex["hops"])

def test_offline_scores_perfect_agent():
    assert all(v == 1.0 for v in offline.run_local(perfect).values())

def test_offline_scores_lazy_agent():
    lazy = lambda q: Result("dunno", [], 1, [])
    s = offline.run_local(lazy); assert s["correct"] == 0.0 and s["enough_searches"] == 0.0
