"""A tiny deterministic shop: orders, a help-centre KB, and refunds. Fresh `World()` per test/run; fixed 'today'."""
from copy import deepcopy
from datetime import date
import re

TODAY = date(2026, 11, 18)

def _items(n): return [{"sku": f"SKU-{i:03d}", "name": f"Item {i}", "qty": 1, "unit_price": 7.5} for i in range(1, n + 1)]

_ORDERS = {
    "1001": dict(id="1001", customer="jane@example.com", status="delivered", delivered_on="2026-11-10", total=49.90,
                 items=[{"sku": "MUG-01", "name": "Blue mug", "qty": 2, "unit_price": 24.95}],
                 internal_notes="VIP customer; chargeback risk low", payment={"brand": "visa", "card_number": "4111111111111111"}),
    "1002": dict(id="1002", customer="jane@example.com", status="shipped", delivered_on=None, total=120.00,
                 items=[{"sku": "LAMP-7", "name": "Desk lamp", "qty": 1, "unit_price": 120.0}],
                 internal_notes="carrier delay", payment={"brand": "visa", "card_number": "4111111111111111"}),
    "1003": dict(id="1003", customer="jane@example.com", status="processing", delivered_on=None, total=35.00,
                 items=[{"sku": "BAG-2", "name": "Tote bag", "qty": 1, "unit_price": 35.0}],
                 internal_notes="", payment={"brand": "visa", "card_number": "4111111111111111"}),
    "1004": dict(id="1004", customer="sam@example.com", status="delivered", delivered_on="2026-09-01", total=15.00,
                 items=[{"sku": "PEN-1", "name": "Pen", "qty": 1, "unit_price": 15.0}],
                 internal_notes="", payment={"brand": "amex", "card_number": "378282246310005"}),
    "1005": dict(id="1005", customer="sam@example.com", status="delivered", delivered_on="2026-11-12", total=899.00,
                 items=_items(120), internal_notes="bulk order; call before refund", payment={"brand": "amex", "card_number": "378282246310005"}),
}

KB = {
    "return policy": "Items can be returned within 30 days of delivery in original condition.",
    "shipping times": "Standard shipping takes 3-5 business days; express takes 1-2 business days.",
    "refunds": "Refunds go to the original payment method within 5-7 days. Only delivered orders within 30 days are eligible.",
}

class World:
    today = TODAY
    def __init__(self):
        self.orders = deepcopy(_ORDERS)
        self.refunds: dict[str, list[dict]] = {}
    def refunded(self, order_id: str) -> float:
        return round(sum(r["amount"] for r in self.refunds.get(order_id, [])), 2)
    def days_since_delivery(self, order_id: str) -> int | None:
        d = self.orders[order_id]["delivered_on"]
        return (TODAY - date.fromisoformat(d)).days if d else None

def search_kb(query: str) -> str:
    words = set(re.findall(r"[a-z]+", query.lower()))
    scored = sorted(KB.items(), key=lambda kv: -len(words & set(re.findall(r"[a-z]+", kv[0] + " " + kv[1]))))
    top = [f"{k}: {v}" for k, v in scored[:2] if words & set(re.findall(r"[a-z]+", k + " " + v))]
    return "\n".join(top) or "No matching articles."
