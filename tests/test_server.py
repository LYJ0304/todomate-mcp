import asyncio
import json
from pathlib import Path

import httpx
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from todomate_mcp.server import server
from todomate_mcp.server import _ConfiguredAdapter
from todomate_mcp.firebase_auth import AuthenticationError
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


def test_mcp_rejects_invalid_tool_inputs():
    async def run():
        async with Client(create_server(Adapter(), today=lambda: __import__("datetime").date(2026, 9, 5))) as client:
            for name, arguments in [
                ("get_todo", {"todo_id": ""}),
                ("create_todo", {"content": ""}),
                ("create_todo", {"content": "valid", "goal_id": ""}),
                ("update_todo", {"todo_id": "one"}),
                ("delete_todo", {"todo_id": ""}),
            ]:
                assert (await client.call_tool(name, arguments)).is_error is True
    asyncio.run(run())


def test_streamable_http_requires_a_bearer_token_and_lists_tools():
    async def run():
        mcp_server = create_server(
            Adapter(),
            today=lambda: __import__("datetime").date(2026, 9, 5),
            access_token="secret",
            resource_server_url="http://testserver/mcp",
        )
        app = mcp_server.streamable_http_app(host="testserver")
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
                response = await client.post("/mcp", json={})
                assert response.status_code == 401
                assert response.headers["www-authenticate"].startswith("Bearer ")

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
                headers={"Authorization": "Bearer secret"},
            ) as http_client:
                async with Client(streamable_http_client("http://testserver/mcp", http_client=http_client)) as client:
                    assert {tool.name for tool in (await client.list_tools()).tools} == {
                        "list_todos",
                        "get_todo",
                        "create_todo",
                        "update_todo",
                        "complete_todo",
                        "delete_todo",
                    }

    asyncio.run(run())


def test_configured_adapter_signs_in_once_before_the_first_operation():
    async def run():
        calls = []

        class Auth:
            refresh_token = "rotated"

            async def sign_in(self, email, password):
                calls.append((email, password))

        class RawAdapter:
            async def list_todos(self, day):
                return [day]

        class Store:
            def save(self, token):
                calls.append(("store", token))

        auth = Auth()

        async def authenticate():
            await auth.sign_in("me@example.com", "password")

        adapter = _ConfiguredAdapter(auth, RawAdapter(), authenticate, Store())
        assert await adapter.list_todos(__import__("datetime").date(2026, 9, 5))
        assert await adapter.list_todos(__import__("datetime").date(2026, 9, 6))
        assert calls == [
            ("me@example.com", "password"),
            ("store", "rotated"),
            ("store", "rotated"),
            ("store", "rotated"),
        ]
    asyncio.run(run())


def test_rejected_refresh_token_requires_reauthentication():
    async def run():
        class Auth:
            refresh_token = "old"

        class Store:
            def save(self, token):
                raise AssertionError("must not save a rejected token")

        async def authenticate():
            raise AuthenticationError("refresh", "http_error", status_code=400)

        adapter = _ConfiguredAdapter(Auth(), object(), authenticate, Store())
        with __import__("pytest").raises(AuthenticationError) as caught:
            await adapter.list_todos(__import__("datetime").date(2026, 9, 5))
        assert (caught.value.operation, caught.value.reason) == ("session", "reauthentication_required")
    asyncio.run(run())
