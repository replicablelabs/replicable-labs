"""KATA 2 (from scratch) - design the OUTPUT of a tool. Run:  uv run kata test k02

lookup_order(world, order_id, include_items=False) -> str   (the string is what the model reads)
  world.orders[order_id] is the raw record (look at katas/world.py). Decide what the model needs, what it must never see,
  how to bound the size, what to say when something is cut off, and what to return when the order does not exist.
  Read tests/test_k02.py for the exact expectations.
"""
import json

def lookup_order(world, order_id: str, include_items: bool = False) -> str:
    raise NotImplementedError
