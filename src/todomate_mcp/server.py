"""TodoMate MCP server entry point."""

import os

import httpx

from .firebase_auth import FirebaseAuthSession
from .firestore import FirestoreClient
from .todomate import TodoMateAdapter
from .tools import create_server


def _adapter_from_environment() -> TodoMateAdapter | None:
    api_key = os.environ.get("TODOMATE_FIREBASE_API_KEY")
    email = os.environ.get("TODOMATE_EMAIL")
    password = os.environ.get("TODOMATE_PASSWORD")
    if not all((api_key, email, password)):
        return None
    client = httpx.AsyncClient()
    auth = FirebaseAuthSession(api_key, client)
    return TodoMateAdapter(auth, FirestoreClient(auth, client))


server = create_server(_adapter_from_environment())


def main() -> None:
    server.run(transport="stdio")
