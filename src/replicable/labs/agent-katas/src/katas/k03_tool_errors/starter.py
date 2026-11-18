"""KATA 3 - tool logic + error messages. Return (content, is_error). Business rules (see tests/test_k03.py):
only delivered orders, within 30 days of delivery, total refunds never above the order total. Errors must tell the model
what is wrong AND what would be valid, so it can recover without guessing."""

def issue_refund(world, order_id: str, amount: float, reason: str) -> tuple[str, bool]:
    order = world.orders[order_id]
    world.refunds.setdefault(order_id, []).append({"amount": amount, "reason": reason})
    return f"refunded {amount}", False
