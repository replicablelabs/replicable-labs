import json

MAX_ITEMS = 5

def lookup_order(world, order_id: str, include_items: bool = False) -> str:
    o = world.orders.get(str(order_id))
    if o is None:
        return f"ERROR: order {order_id!r} not found. Order ids are 4 digits like '1001'; use search_orders to find an id from an email."
    items = o["items"]
    shown = items if include_items else items[:MAX_ITEMS]
    out = {"id": o["id"], "customer": o["customer"], "status": o["status"], "delivered_on": o["delivered_on"],
           "days_since_delivery": world.days_since_delivery(o["id"]),   # derive it for the model: it does not know today's date
           "total": o["total"], "refunded_so_far": world.refunded(o["id"]), "item_count": len(items), "items": shown}
    if len(shown) < len(items):
        out["items_note"] = f"showing {len(shown)} of {len(items)} items; call again with include_items=true to see all"
    return json.dumps(out)   # deliberately omits internal_notes and payment details
