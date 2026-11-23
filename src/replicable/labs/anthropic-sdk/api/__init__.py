"""Enums for the Anthropic Messages API, grouped by which side of the call they sit on.

- `request`: values you SEND (`messages[].role`, the `type` of blocks you build).
- `response`: values you RECEIVE (`response.stop_reason`, the `type` of blocks in
  `response.content`).

Import the modules, not the names, so call sites say which side they mean:
`request.Role.USER`, `response.StopReason.TOOL_USE`.
"""
