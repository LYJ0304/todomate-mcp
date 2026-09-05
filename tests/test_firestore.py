import asyncio
import json

import httpx
import pytest

from todomate_mcp.firestore import FirestoreClient, FirestoreError, decode_fields, encode_fields


class Auth:
    async def id_token(self):
        return "id-token"


def test_codec_round_trip_and_rejects_invalid_values():
    fields = {"name": "task", "done": False, "count": 1, "ratio": 1.5, "none": None, "items": ["x"], "meta": {"a": 1}}
    assert decode_fields(encode_fields(fields)) == fields
    with pytest.raises(ValueError):
        encode_fields({"__reserved__": "x"})
    with pytest.raises(ValueError):
        decode_fields({"count": {"integerValue": "not-an-integer"}})


def test_crud_uses_token_encodes_paths_masks_and_decodes_documents():
    async def run():
        requests = []

        def handle(request):
            requests.append(request)
            assert request.headers["authorization"] == "Bearer id-token"
            if request.method == "DELETE":
                return httpx.Response(200, json={})
            return httpx.Response(200, json={"fields": {"id": {"stringValue": "todo 1"}, "count": {"integerValue": "2"}}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
            firestore = FirestoreClient(Auth(), http)
            assert await firestore.get_document("TodoItem/todo 1") == {"id": "todo 1", "count": 2}
            assert await firestore.upsert_document("TodoItem/todo 1", {"content": "write"}, update_mask=["content"]) == {"id": "todo 1", "count": 2}
            await firestore.delete_document("TodoItem/todo 1")
        assert str(requests[0].url).endswith("/TodoItem/todo%201")
        assert requests[1].url.params.get_list("updateMask.fieldPaths") == ["content"]
        assert json.loads(requests[1].content) == {"fields": {"content": {"stringValue": "write"}}}
    asyncio.run(run())


def test_errors_are_classified_and_document_paths_are_validated():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(403))) as http:
            firestore = FirestoreClient(Auth(), http)
            with pytest.raises(FirestoreError) as caught:
                await firestore.get_document("TodoItem/id")
            assert (caught.value.operation, caught.value.status_code) == ("get", 403)
            with pytest.raises(ValueError):
                await firestore.get_document("TodoItem")
    asyncio.run(run())
