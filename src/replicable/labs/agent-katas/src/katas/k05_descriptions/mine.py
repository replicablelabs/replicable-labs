"""KATA 5 - tool descriptions. The model chooses tools from NAME + DESCRIPTION + parameter descriptions only.
These descriptions are vague/overlapping. Rewrite them, then measure (needs ANTHROPIC_API_KEY):
    uv run python -m katas.live k05_descriptions --runs 3
Edit ONLY SCHEMAS. Be ready to explain: what did you add, why, and what could you have changed instead (tool names, merging tools)?"""

SYSTEM = "You are a customer-support agent for an online shop. Use the tools to help the customer."

SCHEMAS = [{'name': 'lookup_order',
  'description': 'Look up an order.',
  'input_schema': {'type': 'object',
                   'properties': {'order_id': {'type': 'string', 'description': 'id'},
                                  'include_items': {'type': 'boolean', 'description': 'items'}},
                   'required': ['order_id']}},
 {'name': 'search_orders',
  'description': 'Search orders.',
  'input_schema': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'query'}}, 'required': ['query']}},
 {'name': 'issue_refund',
  'description': 'Refund an order.',
  'input_schema': {'type': 'object',
                   'properties': {'order_id': {'type': 'string', 'description': 'order'},
                                  'amount': {'type': 'number', 'description': 'amount'},
                                  'reason': {'type': 'string', 'description': 'reason'}},
                   'required': ['order_id', 'amount', 'reason']}},
 {'name': 'search_kb',
  'description': 'Search.',
  'input_schema': {'type': 'object', 'properties': {'query': {'type': 'string', 'description': 'query'}}, 'required': ['query']}}]
