"""KATA 2 - tool output design. The model reads whatever this returns. Fix it so tests/test_k02.py passes.
Think: what does the model need? what must it never see? what if there is too much?"""
import json

def lookup_order(world, order_id: str, include_items: bool = False) -> str:
    return json.dumps(world.orders.get(order_id))
