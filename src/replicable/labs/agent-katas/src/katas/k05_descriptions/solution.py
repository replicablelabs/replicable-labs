"""KATA 5 reference: precise descriptions (when to use / when NOT to use / formats / preconditions)."""
SYSTEM = "You are a customer-support agent for an online shop. Use the tools to help the customer."

SCHEMAS = [{'name': 'lookup_order',
  'description': "Fetch ONE order by its exact 4-digit order id (e.g. '1001'). Returns status, delivery date, total, amount already "
                 'refunded and the first few items. Use it whenever the customer gives an order id, and to verify an order before any '
                 'refund. Do not use it to find orders by email or name - use search_orders for that.',
  'input_schema': {'type': 'object',
                   'properties': {'order_id': {'type': 'string', 'description': "Bare 4-digit order id, e.g. '1001'. Strip any '#' or 'ORD-' prefix the customer used; never pass words."},
                                  'include_items': {'type': 'boolean',
                                                    'description': 'Set true only if the customer needs the full item list; default shows '
                                                                   'the first 5 items.'}},
                   'required': ['order_id']}},
 {'name': 'search_orders',
  'description': "Find orders when you do NOT have an order id. Pass the customer's email address (or part of it). Returns a short list of "
                 'order ids with status and total; call lookup_order afterwards for details.',
  'input_schema': {'type': 'object',
                   'properties': {'query': {'type': 'string',
                                            'description': "Customer email address or a fragment of it, e.g. 'jane@example.com'."}},
                   'required': ['query']}},
 {'name': 'issue_refund',
  'description': 'Issue a refund for a delivered order. IRREVERSIBLE: call only after lookup_order confirms the order is delivered, within '
                 '30 days of delivery, and the amount is no more than total minus refunded_so_far.',
  'input_schema': {'type': 'object',
                   'properties': {'order_id': {'type': 'string', 'description': "Bare 4-digit order id, e.g. '1001' (no '#' or 'ORD-' prefix)."},
                                  'amount': {'type': 'number',
                                             'description': 'Refund amount in dollars; must not exceed the refundable balance.'},
                                  'reason': {'type': 'string', 'description': 'Short reason given by the customer.'}},
                   'required': ['order_id', 'amount', 'reason']}},
 {'name': 'search_kb',
  'description': 'Search the help-centre knowledge base for company POLICIES (returns, shipping times, refunds). Use for general policy '
                 'questions that are not about one specific order.',
  'input_schema': {'type': 'object',
                   'properties': {'query': {'type': 'string', 'description': "Keywords, e.g. 'return policy'."}},
                   'required': ['query']}}]
