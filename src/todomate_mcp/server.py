"""TodoMate MCP server entry point."""

import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

import httpx

from .firebase_auth import FirebaseAuthSession
from .firestore import FirestoreClient
from .todomate import TodoMateAdapter
from .tools import create_server


class _ConfiguredAdapter:
    def __init__(self, auth: FirebaseAuthSession, adapter: TodoMateAdapter, email: str, password: str):
        self._auth = auth
        self._adapter = adapter
        self._email = email
        self._password: str | None = password
        self._login_lock = asyncio.Lock()

    async def list_todos(self, day: date) -> Any:
        return await self._call(lambda: self._adapter.list_todos(day))

    async def get_todo(self, todo_id: str) -> Any:
        return await self._call(lambda: self._adapter.get_todo(todo_id))

    async def create_todo(self, content: str, day: date, goal_id: str | None) -> Any:
        return await self._call(lambda: self._adapter.create_todo(content, day, goal_id))

    async def update_todo(self, todo_id: str, **fields: Any) -> Any:
        return await self._call(lambda: self._adapter.update_todo(todo_id, **fields))

    async def complete_todo(self, todo_id: str, completed: bool) -> Any:
        return await self._call(lambda: self._adapter.complete_todo(todo_id, completed))

    async def delete_todo(self, todo_id: str) -> None:
        await self._call(lambda: self._adapter.delete_todo(todo_id))

    async def _call(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        if self._password is not None:
            async with self._login_lock:
                if self._password is not None:
                    await self._auth.sign_in(self._email, self._password)
                    self._password = None
        return await operation()


def _adapter_from_environment() -> _ConfiguredAdapter | None:
    api_key = os.environ.get("TODOMATE_FIREBASE_API_KEY")
    email = os.environ.get("TODOMATE_EMAIL")
    password = os.environ.get("TODOMATE_PASSWORD")
    if not all((api_key, email, password)):
        return None
    client = httpx.AsyncClient()
    auth = FirebaseAuthSession(api_key, client)
    return _ConfiguredAdapter(auth, TodoMateAdapter(auth, FirestoreClient(auth, client)), email, password)


server = create_server(_adapter_from_environment())


def main() -> None:
    server.run(transport="stdio")
