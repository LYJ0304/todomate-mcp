"""TodoMate MCP server entry point."""

from mcp.server.mcpserver import MCPServer

server = MCPServer(
    name="TodoMate",
    instructions="TodoMate MCP server. Todo tools will be added in subsequent releases.",
)


def main() -> None:
    server.run(transport="stdio")
