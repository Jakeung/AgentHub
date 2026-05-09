"""Chat API - WebSocket streaming + REST for history."""
import json
import logging
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db, async_session
from app.models.instance import AgentInstance
from app.models.conversation import Conversation
from app.services import chat_service
from app.core.response import success, page_data
from app.core.exceptions import BusinessError
from app.core.auth import verify_token_from_cookie

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

MAX_CONNECTIONS_PER_INSTANCE = 5


class ConnectionManager:
    """Manage WebSocket connections: one per user per instance."""

    def __init__(self):
        self._connections: dict[tuple[int, int], WebSocket] = {}

    async def connect(self, instance_id: int, user_id: int, websocket: WebSocket) -> bool:
        key = (instance_id, user_id)

        # Disconnect old connection for same user+instance
        if key in self._connections:
            old_ws = self._connections[key]
            try:
                await old_ws.close(code=1000, reason="新连接已建立")
            except Exception:
                pass

        # Check per-instance connection limit
        instance_count = sum(
            1 for (iid, _) in self._connections if iid == instance_id
        )
        if instance_count >= MAX_CONNECTIONS_PER_INSTANCE:
            return False

        self._connections[key] = websocket
        return True

    def disconnect(self, instance_id: int, user_id: int):
        self._connections.pop((instance_id, user_id), None)

    @property
    def active_count(self) -> int:
        return len(self._connections)


ws_manager = ConnectionManager()


# ─── REST: Conversation & Message History ───


@router.get("/api/chat/conversations")
async def list_conversations(
    request: Request,
    instance_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    convs, total = await chat_service.list_conversations(
        db, user_id, instance_id, page, page_size
    )
    items = [
        {
            "uuid": c.uuid,
            "title": c.title,
            "instance_id": c.instance_id,
            "message_count": c.message_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convs
    ]
    return page_data(items, total, page, page_size)


@router.get("/api/chat/conversations/{conversation_uuid}/messages")
async def get_messages(
    request: Request,
    conversation_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    messages = await chat_service.get_messages(db, conversation_uuid, user_id)
    items = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
    return success(items)


@router.delete("/api/chat/conversations/{conversation_uuid}")
async def delete_conversation(
    request: Request,
    conversation_uuid: str,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    result = await db.execute(
        select(Conversation).where(
            Conversation.uuid == conversation_uuid,
            Conversation.user_id == user_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise BusinessError(-4, "会话不存在")
    await db.delete(conv)
    await db.commit()
    return success(None)


# ─── WebSocket: Streaming Chat ───


@router.websocket("/ws/chat/{instance_id}")
async def ws_chat(websocket: WebSocket, instance_id: int):
    """WebSocket endpoint for streaming chat with a Hermes instance."""
    # Auth from cookie
    token = websocket.cookies.get("auth-token")
    if not token:
        await websocket.close(code=4001, reason="未登录")
        return

    payload = verify_token_from_cookie(token)
    if not payload:
        await websocket.close(code=4001, reason="Token 无效")
        return

    user_id = payload.get("id")

    # Register connection with manager
    await websocket.accept()
    if not await ws_manager.connect(instance_id, user_id, websocket):
        await websocket.send_json({"type": "error", "message": "该实例连接数已满"})
        await websocket.close(code=4029)
        return

    # Verify instance ownership
    async with async_session() as db:
        result = await db.execute(
            select(AgentInstance).where(
                AgentInstance.id == instance_id,
                AgentInstance.owner_user_id == user_id,
                AgentInstance.status != "deleted",
            )
        )
        instance = result.scalar_one_or_none()

    if not instance:
        await websocket.send_json({"type": "error", "message": "实例不存在或无权访问"})
        await websocket.close(code=4004)
        return

    if instance.status != "running":
        await websocket.send_json({"type": "error", "message": f"实例未运行 (当前状态: {instance.status})"})
        await websocket.close(code=4003)
        return

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "消息格式错误"})
                continue

            msg_type = data.get("type", "message")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    await websocket.send_json({"type": "error", "message": "消息内容不能为空"})
                    continue

                conversation_uuid = data.get("conversation_id")

                async with async_session() as db:
                    conversation = await chat_service.get_or_create_conversation(
                        db, conversation_uuid, instance_id, user_id
                    )

                    # Send conversation_id to client
                    await websocket.send_json({
                        "type": "conversation_id",
                        "conversation_id": conversation.uuid,
                    })

                    # Stream response
                    model = data.get("model")
                    async for chunk in chat_service.stream_chat(
                        db, instance, conversation, content, model=model
                    ):
                        await websocket.send_json({
                            "type": "chunk",
                            "content": chunk,
                            "conversation_id": conversation.uuid,
                        })

                    await websocket.send_json({
                        "type": "done",
                        "conversation_id": conversation.uuid,
                    })

    except WebSocketDisconnect:
        ws_manager.disconnect(instance_id, user_id)
        logger.info(f"WebSocket disconnected: user={user_id} instance={instance_id}")
    except Exception as e:
        ws_manager.disconnect(instance_id, user_id)
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)[:200]})
        except Exception:
            pass
