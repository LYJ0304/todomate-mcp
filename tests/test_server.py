import asyncio
import json
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from todomate_mcp.server import server
from todomate_mcp.server import _ConfiguredAdapter
from todomate_mcp.models import Todo
from todomate_mcp.tools import create_server


def test_server_initializes_and_lists_tools():
    async def run():
        async with Client(server) as client:
            assert {tool.name for tool in (await client.list_tools()).tools} == {"list_todos", "get_todo", "create_todo", "update_todo", "complete_todo", "delete_todo"}
    asyncio.run(run())


def test_stdio_entry_point_connects():
    async def run():
        params = StdioServerParameters(
            command="uv", args=["run", "todomate-mcp"], cwd=Path(__file__).parents[1]
        )
        async with Client(stdio_client(params)) as client:
            assert {tool.name for tool in (await client.list_tools()).tools} == {"list_todos", "get_todo", "create_todo", "update_todo", "complete_todo", "delete_todo"}
    asyncio.run(run())


class Adapter:
    async def list_todos(self, day):
        assert day.isoformat() == "2026-09-05"
        return [Todo(id="one", content="write", date=day, completed=False, goal_id="goal")]

    async def get_todo(self, todo_id):
        return Todo(id=todo_id, content="write", date=__import__("datetime").date(2026, 9, 5), completed=False, goal_id="goal")

    async def create_todo(self, content, day, goal_id):
        assert (content, day.isoformat(), goal_id) == ("new", "2026-09-05", None)
        return Todo(id="new", content=content, date=day, completed=False, goal_id=goal_id)

    async def update_todo(self, todo_id, *, content=None, day=None, goal_id=None):
        assert (todo_id, content, day, goal_id) == ("one", "changed", None, None)
        return Todo(id=todo_id, content=content, date=__import__("datetime").date(2026, 9, 5), completed=False, goal_id="goal")

    async def complete_todo(self, todo_id, completed=True):
        assert (todo_id, completed) == ("one", False)
        return Todo(id=todo_id, content="write", date=__import__("datetime").date(2026, 9, 5), completed=completed, goal_id="goal")

    async def delete_todo(self, todo_id):
        assert todo_id == "one"


def test_todo_tools_list_and_return_normalized_data():
    async def run():
        async with Client(create_server(Adapter(), today=lambda: __import__("datetime").date(2026, 9, 5))) as client:
            assert {tool.name for tool in (await client.list_tools()).tools} == {"list_todos", "get_todo", "create_todo", "update_todo", "complete_todo", "delete_todo"}
            listed = await client.call_tool("list_todos")
            fetched = await client.call_tool("get_todo", {"todo_id": "one"})
            created = await client.call_tool("create_todo", {"content": "new"})
            updated = await client.call_tool("update_todo", {"todo_id": "one", "content": "changed"})
            completed = await client.call_tool("complete_todo", {"todo_id": "one", "completed": False})
            deleted = await client.call_tool("delete_todo", {"todo_id": "one"})
            assert json.loads(listed.content[0].text)["todos"][0]["id"] == "one"
            assert json.loads(fetched.content[0].text)["id"] == "one"
            assert json.loads(created.content[0].text)["id"] == "new"
            assert json.loads(updated.content[0].text)["content"] == "changed"
            assert json.loads(completed.content[0].text)["completed"] is False
            assert json.loads(deleted.content[0].text) == {"id": "one", "deleted": True}
    asyncio.run(run())


def test_configured_adapter_signs_in_once_before_the_first_operation():
    async def run():
        calls = []

        class Auth:
            async def sign_in(self, email, password):
                calls.append((email, password))

        class RawAdapter:
            async def list_todos(self, day):
                return [day]

        adapter = _ConfiguredAdapter(Auth(), RawAdapter(), "me@example.com", "password")
        assert await adapter.list_todos(__import__("datetime").date(2026, 9, 5))
        assert await adapter.list_todos(__import__("datetime").date(2026, 9, 6))
        assert calls == [("me@example.com", "password")]
    asyncio.run(run())
