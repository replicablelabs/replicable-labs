"""KATA 3 (from scratch) - tool logic + error messages. Run:  uv run kata test k03

issue_refund(world, order_id, amount, reason) -> (content: str, is_error: bool)
  Rules: order must exist; amount a positive number; only DELIVERED orders; within 30 days of delivery
  (world.days_since_delivery(order_id)); total refunds never above the order total (world.refunded(order_id)).
  On success record it in world.refunds[order_id] and return an id like R-<order>-<n>. On failure change NOTHING and return an error
  that tells the model what is wrong AND what would be valid. Read tests/test_k03.py for exact expectations.
"""

def issue_refund(world, order_id: str, amount: float, reason: str) -> tuple[str, bool]:
    raise NotImplementedError
