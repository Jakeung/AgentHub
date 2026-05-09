"""Chat API tests (REST only, no WebSocket streaming)."""
import pytest
import uuid
from httpx import AsyncClient


async def _seed_conversation(client: AsyncClient, user_cookies, title="Test Conv"):
    """Helper: seed a conversation directly via DB."""
    from tests.conftest import _test_session_maker
    from app.models.conversation import Conversation, Message

    # Get user_id from /me
    me_resp = await client.get("/api/auth/me", cookies=user_cookies)
    user_id = me_resp.json()["data"]["id"]

    conv_uuid = str(uuid.uuid4())
    async with _test_session_maker() as db:
        conv = Conversation(
            uuid=conv_uuid,
            title=title,
            instance_id=1,
            user_id=user_id,
            message_count=2,
        )
        db.add(conv)
        await db.flush()

        db.add(Message(conversation_id=conv.id, role="user", content="Hello"))
        db.add(Message(conversation_id=conv.id, role="assistant", content="Hi there!"))
        await db.commit()

    return conv_uuid


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient, user_cookies):
    resp = await client.get("/api/chat/conversations", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] >= 0


@pytest.mark.asyncio
async def test_list_conversations_with_data(client: AsyncClient, user_cookies):
    conv_uuid = await _seed_conversation(client, user_cookies, title="Seeded Conv")

    resp = await client.get("/api/chat/conversations", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    uuids = [c["uuid"] for c in data["data"]["items"]]
    assert conv_uuid in uuids


@pytest.mark.asyncio
async def test_get_messages(client: AsyncClient, user_cookies):
    conv_uuid = await _seed_conversation(client, user_cookies, title="Msg Conv")

    resp = await client.get(f"/api/chat/conversations/{conv_uuid}/messages", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert len(data["data"]) == 2
    assert data["data"][0]["role"] == "user"
    assert data["data"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient, user_cookies):
    conv_uuid = await _seed_conversation(client, user_cookies, title="Delete Conv")

    resp = await client.delete(f"/api/chat/conversations/{conv_uuid}", cookies=user_cookies)
    assert resp.json()["code"] == 0

    # Verify it's gone
    list_resp = await client.get("/api/chat/conversations", cookies=user_cookies)
    uuids = [c["uuid"] for c in list_resp.json()["data"]["items"]]
    assert conv_uuid not in uuids


@pytest.mark.asyncio
async def test_delete_conversation_not_owned(client: AsyncClient, user_cookies, second_user_cookies):
    conv_uuid = await _seed_conversation(client, user_cookies, title="Not Owned")

    resp = await client.delete(f"/api/chat/conversations/{conv_uuid}", cookies=second_user_cookies)
    data = resp.json()
    assert data["code"] == -4


@pytest.mark.asyncio
async def test_list_conversations_pagination(client: AsyncClient, user_cookies):
    for i in range(3):
        await _seed_conversation(client, user_cookies, title=f"Page Conv {i}")

    resp = await client.get("/api/chat/conversations?page=1&page_size=2", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert len(data["data"]["items"]) <= 2
    assert data["data"]["total"] >= 3
