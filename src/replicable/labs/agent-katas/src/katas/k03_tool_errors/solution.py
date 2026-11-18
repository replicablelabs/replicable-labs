def issue_refund(world, order_id: str, amount: float, reason: str) -> tuple[str, bool]:
    o = world.orders.get(str(order_id))
    if o is None: return f"ERROR: order {order_id!r} not found. Verify the id with lookup_order or search_orders.", True
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
        return f"ERROR: amount must be a positive number (got {amount!r}).", True
    if o["status"] != "delivered":
        return f"ERROR: only delivered orders can be refunded; order {order_id} is '{o['status']}'.", True
    days = world.days_since_delivery(order_id)
    if days > 30:
        return f"ERROR: order {order_id} was delivered {days} days ago; refunds are only allowed within 30 days of delivery.", True
    remaining = round(o["total"] - world.refunded(order_id), 2)
    if amount > remaining + 1e-9:
        return f"ERROR: amount {amount:.2f} exceeds the refundable balance of {remaining:.2f} for order {order_id}.", True
    n = len(world.refunds.get(order_id, [])) + 1
    world.refunds.setdefault(order_id, []).append({"amount": round(float(amount), 2), "reason": reason})
    return f"OK: refund R-{order_id}-{n} of {amount:.2f} issued. Remaining refundable balance: {remaining - amount:.2f}.", False
