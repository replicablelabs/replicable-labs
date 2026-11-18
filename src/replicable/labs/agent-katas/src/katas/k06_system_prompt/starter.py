"""KATA 6 - system prompt / agent policy. Tools are fine (reference descriptions from kata 5). The refund tool is deliberately PERMISSIVE
(it only checks the order exists), so the POLICY must live in your prompt: delivered orders only, within 30 days, never above the
remaining balance, ONE refund per order, refunds above $100 need human approval (do not issue them), and ask for the order id if it
is missing. The current prompt knows none of this.
Rewrite SYSTEM, then measure (needs ANTHROPIC_API_KEY):
    uv run python -m katas.live k06_system_prompt --runs 3
Edit ONLY SYSTEM. Be ready to discuss: what belongs in the prompt vs in tool code (e.g. should the 30-day rule live ONLY in
the prompt?), how you would regression-test a prompt change, and what you would log in production."""
from katas.k05_descriptions.solution import SCHEMAS  # noqa: F401  (tools are fixed for this kata)

SYSTEM = "You are a helpful customer support assistant."
