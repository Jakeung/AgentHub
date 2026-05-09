"""Audit logging service — records user operations to sys_operation_log."""
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import SysOperationLog


async def log_operation(
    db: AsyncSession,
    *,
    user_id: int | None,
    action: str,
    target_type: str = "",
    target_id: int | None = None,
    detail: dict | None = None,
    ip_address: str = "",
):
    """Write one audit log row. Caller must commit the session to persist."""
    entry = SysOperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=json.dumps(detail or {}, ensure_ascii=False),
        ip_address=ip_address,
    )
    db.add(entry)
    # Flush so the row is written even if caller doesn't explicitly commit
    await db.flush()
