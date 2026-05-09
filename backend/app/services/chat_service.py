"""Chat service - conversation management and streaming proxy."""
import uuid
import logging
from typing import AsyncIterator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.instance import AgentInstance
from app.adapters.hermes_adapter import HermesAdapter
from app.core.exceptions import BusinessError

logger = logging.getLogger(__name__)


async def get_or_create_conversation(
    db: AsyncSession,
    conversation_uuid: str | None,
    instance_id: int,
    user_id: int,
) -> Conversation:
    """Get existing conversation by UUID or create a new one."""
    if conversation_uuid:
        result = await db.execute(
            select(Conversation).where(
                Conversation.uuid == conversation_uuid,
                Conversation.user_id == user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    # Create new
    conv = Conversation(
        uuid=conversation_uuid or str(uuid.uuid4()),
        instance_id=instance_id,
        user_id=user_id,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def save_message(
    db: AsyncSession,
    conversation_id: int,
    role: str,
    content: str,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    db.add(msg)

    # Update conversation
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = conv_result.scalar_one()
    conv.message_count = (conv.message_count or 0) + 1

    # Auto-title from first user message
    if role == "user" and conv.message_count <= 1:
        conv.title = content[:50] + ("..." if len(content) > 50 else "")

    await db.commit()
    await db.refresh(msg)
    return msg


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: int,
    limit: int = 50,
) -> list[dict]:
    """Get messages for building the chat context."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id.asc())
        .limit(limit)
    )
    return [
        {"role": m.role, "content": m.content}
        for m in result.scalars().all()
    ]


async def stream_chat(
    db: AsyncSession,
    instance: AgentInstance,
    conversation: Conversation,
    user_message: str,
    model: str | None = None,
) -> AsyncIterator[str]:
    """Save user message, build context, stream response from Hermes, save assistant reply."""
    # Save user message
    await save_message(db, conversation.id, "user", user_message)

    # Build context from history
    messages = await get_conversation_messages(db, conversation.id)

    # Stream from Hermes
    adapter = HermesAdapter(port=instance.port, api_key=instance.api_server_key or "", container_name=instance.container_name or "")
    full_response = []

    try:
        async for chunk in adapter.chat_stream(messages=messages, **(dict(model=model) if model else {})):
            full_response.append(chunk)
            yield chunk
    except Exception as e:
        logger.error(f"Hermes stream error: {e}")
        error_msg = f"Agent 通信错误: {str(e)[:200]}"
        yield f"\n\n[错误] {error_msg}"
        full_response.append(f"\n\n[错误] {error_msg}")

    # Save assistant response
    if full_response:
        await save_message(db, conversation.id, "assistant", "".join(full_response))


async def list_conversations(
    db: AsyncSession,
    user_id: int,
    instance_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Conversation], int]:
    query = select(Conversation).where(Conversation.user_id == user_id)
    if instance_id:
        query = query.where(Conversation.instance_id == instance_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Conversation.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    return result.scalars().all(), total


async def get_messages(
    db: AsyncSession,
    conversation_uuid: str,
    user_id: int,
) -> list[Message]:
    """Get all messages for a conversation."""
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.uuid == conversation_uuid,
            Conversation.user_id == user_id,
        )
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise BusinessError(-4, "会话不存在")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.id.asc())
    )
    return result.scalars().all()
