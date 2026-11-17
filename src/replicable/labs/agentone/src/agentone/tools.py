"""Tool registry: JSON schema (what the model sees) + python callable (what we run)."""
from __future__ import annotations
import ast, operator as op
from typing import Any, Callable
from . import graphrag

_corpus = graphrag.load()
GRAPH = graphrag.build_graph(_corpus["triples"])
DOCS = _corpus["docs"]

_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg}

def _eval(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS: return _OPS[type(n.op)](_eval(n.left), _eval(n.right))
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS: return _OPS[type(n.op)](_eval(n.operand))
    raise ValueError("unsupported expression")

def calculator(expression: str) -> str:
    return str(_eval(ast.parse(expression, mode="eval").body))

def graph_search(query: str, hops: int = 2) -> str:
    return graphrag.retrieve(query, GRAPH, DOCS, hops) or "no results"

# name -> (callable, anthropic tool schema)
TOOLS: dict[str, tuple[Callable[..., str], dict[str, Any]]] = {
    "calculator": (calculator, {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression, e.g. '2*(3+4)'.",
        "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
    }),
    "graph_search": (graph_search, {
        "name": "graph_search",
        "description": "Search the company knowledge graph. Pass a question naming entities; returns related facts as 'A --relation--> B'. Use several times to chase multi-hop questions.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "hops": {"type": "integer", "default": 2}}, "required": ["query"]},
    }),
}

def schemas() -> list[dict]: return [s for _, s in TOOLS.values()]

def run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Returns (content, is_error). Never raise into the loop: errors go back to the model."""
    if name not in TOOLS: return f"unknown tool {name}", True
    try: return TOOLS[name][0](**args), False
    except Exception as e: return f"{type(e).__name__}: {e}", True
