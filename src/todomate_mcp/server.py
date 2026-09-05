"""TodoMate MCP server entry point."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

import httpx

from .firebase_auth import AuthenticationError, FirebaseAuthSession
from .firestore import FirestoreClient
from .settings import RefreshTokenStore, load_auth_settings
from .todomate import TodoMateAdapter
from .tools import create_server


class _ConfiguredAdapter:
    def __init__(
        self,
        auth: FirebaseAuthSession,
        adapter: TodoMateAdapter,
        authenticate: Callable[[], Awaitable[None]],
        token_store: RefreshTokenStore,
    ):
        self._auth = auth
        self._adapter = adapter
        self._authenticate: Callable[[], Awaitable[None]] | None = authenticate
        self._token_store = token_store
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
        if self._authenticate is not None:
            async with self._login_lock:
                if self._authenticate is not None:
                    try:
                        await self._authenticate()
                    except AuthenticationError as error:
                        raise _reauthentication_error(error) from None
                    self._authenticate = None
                    self._token_store.save(self._auth.refresh_token)
        try:
            result = await operation()
        except AuthenticationError as error:
            raise _reauthentication_error(error) from None
        self._token_store.save(self._auth.refresh_token)
        return result


def _adapter_from_environment() -> _ConfiguredAdapter | None:
    settings = load_auth_settings()
    if settings is None:
        return None
    client = httpx.AsyncClient()
    auth = FirebaseAuthSession(settings.api_key, client)
    if settings.refresh_token:
        authenticate = lambda: auth.restore(settings.refresh_token or "")
    else:
        authenticate = lambda: auth.sign_in(settings.email or "", settings.password or "")
    return _ConfiguredAdapter(
        auth, TodoMateAdapter(auth, FirestoreClient(auth, client)), authenticate, RefreshTokenStore()
    )


def _reauthentication_error(error: AuthenticationError) -> AuthenticationError:
    if error.operation == "refresh" and error.status_code in {400, 401}:
        return AuthenticationError("session", "reauthentication_required", status_code=error.status_code)
    return error


server = create_server(_adapter_from_environment())


def main() -> None:
    server.run(transport="stdio")
