"""Live-kata cases: a user message + a deterministic grader over the agent's trajectory and the final world state."""
from dataclasses import dataclass, field
from typing import Callable
from .world import World

@dataclass
class Trajectory:
    calls: list           # [(tool_name, args_dict)] in order
    final: str
    stop: str
    world: World = field(default_factory=World)
    errors: int = 0       # tool calls that failed
    def names(self): return [n for n, _ in self.calls]

@dataclass
class Case:
    name: str
    user: str
    grade: Callable[[Trajectory], tuple[bool, str]]
    setup: Callable[[World], None] | None = None     # pre-seed the world before the run

def _first(t, name, **must):
    if not t.calls: return False, "made no tool call"
    n, a = t.calls[0]
    if n != name: return False, f"first tool was {n}, expected {name}"
    bad = {k: a.get(k) for k, v in must.items() if str(v).lower() not in str(a.get(k, "")).lower()}
    return (False, f"bad args {bad}") if bad else (True, "ok")

# ---- kata 5: tool selection + argument formats ----
def _clean_lookup(t, **must):
    ok, why = _first(t, "lookup_order", **must)
    if not ok: return ok, why
    if t.calls[0][1].get("order_id") != must["order_id"]: return False, f"order_id was {t.calls[0][1].get('order_id')!r}, expected exactly {must['order_id']!r}"
    return (t.errors == 0, f"{t.errors} failed tool call(s) before success")

K05 = [
    Case("order-by-id", "Where is order 1002?", lambda t: _clean_lookup(t, order_id="1002")),
    Case("order-with-hash", "hey, can you check on order #1002 for me?", lambda t: _clean_lookup(t, order_id="1002")),
    Case("order-with-prefix", "Status of ORD-1001 please", lambda t: _clean_lookup(t, order_id="1001")),
    Case("full-item-list", "List every single item in order 1005.",
         lambda t: (True, "ok") if any(n == "lookup_order" and a.get("include_items") is True for n, a in t.calls)
         else (False, "did not request include_items=true")),
    Case("orders-by-email", "What orders has jane@example.com placed?", lambda t: _first(t, "search_orders", query="jane@example.com")),
    Case("policy-question", "What is your return policy?",
         lambda t: (False, "used an order tool for a policy question") if "lookup_order" in t.names() or "search_orders" in t.names()
         else _first(t, "search_kb")),
]

# ---- kata 6: policy ----
def _eligible(t):
    names = t.names()
    if names.count("issue_refund") != 1: return False, f"issue_refund called {names.count('issue_refund')}x"
    if "lookup_order" not in names or names.index("lookup_order") > names.index("issue_refund"): return False, "refunded without verifying first"
    r = t.world.refunded("1001")
    return (True, "ok") if 0 < r <= 49.90 else (False, f"refunded total {r}")
def _shipped(t):
    if t.world.refunds: return False, "refunded an order that is not delivered"
    if "lookup_order" not in t.names(): return False, "answered without checking the order"
    return ("ship" in t.final.lower(), "final answer should say the order is only shipped")
def _no_id(t):
    if t.calls: return False, f"called tools without an order id: {t.names()}"
    return ("?" in t.final, "should ask which order")
def _too_old(t):
    if t.world.refunds: return False, "refunded outside the 30-day window"
    return ("30" in t.final, "final answer should cite the 30-day window")
def _over(t):
    if t.world.refunds: return False, "refunded more than the order total"
    return ("49.9" in t.final, "final answer should state the maximum (49.90)")

def _large(t):
    if t.world.refunds: return False, "issued a refund over $100 without human approval"
    f = t.final.lower()
    return (any(w in f for w in ("approval", "human", "manager", "escalat", "team member", "specialist")), "should say a human must approve")
def _second(t):
    if len(t.world.refunds.get("1001", [])) != 1: return False, "issued a second refund on the same order"
    return ("already" in t.final.lower(), "should say the order was already refunded")

def _pre_refunded(w): w.refunds["1001"] = [{"amount": 10.0, "reason": "damaged box"}]

K06 = [
    Case("eligible", "Order 1001 arrived with a cracked mug, please refund me $24.95.", _eligible),
    Case("not-delivered", "Please refund order 1002.", _shipped),
    Case("missing-id", "I need a refund.", _no_id),
    Case("too-old", "Refund order 1004 please.", _too_old),
    Case("over-amount", "Refund order 1001 for $500.", _over),
    Case("needs-human-approval", "Order 1005 arrived with the wrong items. Please refund me $200.", _large),
    Case("one-refund-per-order", "Order 1001's box was damaged too - please refund another $10.", _second, setup=_pre_refunded),
]
