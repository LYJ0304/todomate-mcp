import asyncio
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from todomate_mcp.server import server


def test_server_initializes_and_lists_no_tools():
    async def run():
        async with Client(server) as client:
            assert (await client.list_tools()).tools == []
    asyncio.run(run())


def test_stdio_entry_point_connects():
    async def run():
        params = StdioServerParameters(
            command="uv", args=["run", "todomate-mcp"], cwd=Path(__file__).parents[1]
        )
        async with Client(stdio_client(params)) as client:
            assert (await client.list_tools()).tools == []
    asyncio.run(run())
