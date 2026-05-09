"""Admin audit log query API."""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.models.audit import SysOperationLog
from app.models.user import SysUser
from app.core.response import page_data

router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin-audit"])


def _log_to_dict(log: SysOperationLog, username: str = "") -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": username,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("")
async def list_audit_logs(
    action: str | None = None,
    user_id: int | None = None,
    target_type: str | None = None,
    keyword: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(SysOperationLog)

    if action:
        query = query.where(SysOperationLog.action == action)
    if user_id:
        query = query.where(SysOperationLog.user_id == user_id)
    if target_type:
        query = query.where(SysOperationLog.target_type == target_type)
    if keyword:
        query = query.where(SysOperationLog.detail.contains(keyword))
    if start_date:
        query = query.where(SysOperationLog.created_at >= start_date)
    if end_date:
        query = query.where(SysOperationLog.created_at <= end_date)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(SysOperationLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    # Enrich with usernames
    user_ids = {l.user_id for l in logs if l.user_id}
    users = {}
    if user_ids:
        user_result = await db.execute(
            select(SysUser.id, SysUser.username).where(SysUser.id.in_(user_ids))
        )
        users = {r[0]: r[1] for r in user_result.all()}

    items = [_log_to_dict(l, users.get(l.user_id, "")) for l in logs]
    return page_data(items, total, page, page_size)
