"""Claude Agent SDK: the Claude Code harness as a library. The loop is built in; you supply tools/permissions/hooks.
Needs the `claude` CLI auth or ANTHROPIC_API_KEY."""
import asyncio
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool, AssistantMessage, ResultMessage, TextBlock
from . import tools as T

@tool("graph_search", "Search the company knowledge graph (multi-hop facts).", {"query": str})
async def graph_search(args):
    return {"content": [{"type": "text", "text": T.graph_search(args["query"])}]}

server = create_sdk_mcp_server(name="kg", version="1.0.0", tools=[graph_search])

OPTIONS = ClaudeAgentOptions(
    mcp_servers={"kg": server},
    allowed_tools=["mcp__kg__graph_search"],   # tool names are mcp__<server>__<tool>
    system_prompt="Answer using graph_search. Chase multi-hop questions.",
    max_turns=8,
)

async def ask(q: str) -> str:
    out = ""
    async for m in query(prompt=q, options=OPTIONS):
        if isinstance(m, AssistantMessage):
            out += "".join(b.text for b in m.content if isinstance(b, TextBlock))
        elif isinstance(m, ResultMessage):
            break
    return out

if __name__ == "__main__":
    print(asyncio.run(ask("Who leads the team that owns the Schema Registry?")))
