"""Tool implementations used by the LIVE katas (5 and 6). Reuses the reference solutions of katas 2 and 3."""
import json
from . import world as W
from .k02_tool_output.solution import lookup_order
from .k03_tool_errors.solution import issue_refund

class ToolError(Exception): pass

def impls(world: W.World, enforce_refund_rules: bool = True) -> dict:
    def _lookup(order_id, include_items=False):
        out = lookup_order(world, order_id, include_items)
        if out.startswith("ERROR"): raise ToolError(out)
        return out
    def _search_orders(query):
        q = str(query).lower()
        hits = [{"id": o["id"], "status": o["status"], "total": o["total"]} for o in world.orders.values()
                if q in o["customer"].lower() or q == o["id"]]
        return json.dumps(hits) if hits else "No orders found. Search needs a customer email (or part of one)."
    def _permissive_refund(order_id, amount, reason):
        """Only checks the order exists and the amount is positive: the POLICY must then live in the system prompt."""
        if str(order_id) not in world.orders: raise ToolError(f"ERROR: order {order_id!r} not found.")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0: raise ToolError("ERROR: amount must be positive.")
        world.refunds.setdefault(str(order_id), []).append({"amount": round(float(amount), 2), "reason": reason})
        return f"OK: refund of {amount:.2f} issued for order {order_id}."
    def _refund(order_id, amount, reason):
        if not enforce_refund_rules: return _permissive_refund(order_id, amount, reason)
        content, err = issue_refund(world, order_id, amount, reason)
        if err: raise ToolError(content)
        return content
    return {"lookup_order": _lookup, "search_orders": _search_orders, "issue_refund": _refund,
            "search_kb": lambda query: W.search_kb(query)}
