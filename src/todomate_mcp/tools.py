"""MCP tools for TodoMate."""

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from mcp.server.mcpserver import MCPServer

from .todomate import TodoMateAdapter, TodoNotFoundError

_TIME_ZONE = ZoneInfo("Asia/Seoul")


def create_server(adapter: TodoMateAdapter | None, *, today: Callable[[], date] | None = None) -> MCPServer:
    mcp = MCPServer(
        name="TodoMate",
        instructions="TodoMate todos. Dates without a value use today's date in Asia/Seoul.",
    )
    today = today or (lambda: datetime.now(_TIME_ZONE).date())

    def configured() -> TodoMateAdapter:
        if adapter is None:
            raise RuntimeError("TodoMate credentials are not configured")
        return adapter

    @mcp.tool(description="List the authenticated user's todos for a date. Defaults to today in Asia/Seoul.")
    async def list_todos(day: date | None = None) -> dict:
        return {"todos": [todo.model_dump(mode="json") for todo in await configured().list_todos(day or today())]}

    @mcp.tool(description="Get one of the authenticated user's todos by ID.")
    async def get_todo(todo_id: str) -> dict:
        try:
            return (await configured().get_todo(todo_id)).model_dump(mode="json")
        except TodoNotFoundError:
            raise ValueError("Todo not found") from None

    @mcp.tool(description="Create a todo for the authenticated user. Date defaults to today in Asia/Seoul.")
    async def create_todo(content: str, day: date | None = None, goal_id: str | None = None) -> dict:
        return (await configured().create_todo(content, day or today(), goal_id)).model_dump(mode="json")

    return mcp
