"""Admin dashboard aggregation API."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db
from app.models.user import SysUser
from app.models.instance import AgentInstance, InstanceModelConfig
from app.models.conversation import Conversation, Message
from app.models.audit import SysOperationLog
from app.core.response import success

router = APIRouter(prefix="/api/admin/dashboard", tags=["admin-dashboard"])


@router.get("")
async def get_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    # --- Stats ---
    user_total = (await db.execute(
        select(func.count()).select_from(SysUser).where(SysUser.status == "active")
    )).scalar() or 0

    user_new_week = (await db.execute(
        select(func.count()).select_from(SysUser).where(SysUser.created_at >= week_ago)
    )).scalar() or 0

    instance_total = (await db.execute(
        select(func.count()).select_from(AgentInstance).where(AgentInstance.status != "deleted")
    )).scalar() or 0

    instance_new_week = (await db.execute(
        select(func.count()).select_from(AgentInstance).where(
            AgentInstance.created_at >= week_ago,
            AgentInstance.status != "deleted",
        )
    )).scalar() or 0

    instance_running = (await db.execute(
        select(func.count()).select_from(AgentInstance).where(AgentInstance.status == "running")
    )).scalar() or 0

    conv_today = (await db.execute(
        select(func.count()).select_from(Conversation).where(Conversation.created_at >= today)
    )).scalar() or 0

    conv_yesterday = (await db.execute(
        select(func.count()).select_from(Conversation).where(
            Conversation.created_at >= yesterday,
            Conversation.created_at < today,
        )
    )).scalar() or 0

    # --- Instance status distribution ---
    status_rows = (await db.execute(
        select(AgentInstance.status, func.count()).where(
            AgentInstance.status != "deleted"
        ).group_by(AgentInstance.status)
    )).all()
    instance_status = {row[0]: row[1] for row in status_rows}

    # --- Token trend (7 days) ---
    token_rows = (await db.execute(
        select(
            func.date(Message.created_at).label("date"),
            func.coalesce(func.sum(Message.token_count), 0).label("tokens"),
        ).where(Message.created_at >= week_ago)
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
    )).all()
    token_trend = [{"date": str(r[0]), "tokens": r[1]} for r in token_rows]

    # --- Activity trend (7 days) ---
    user_trend_rows = (await db.execute(
        select(
            func.date(SysUser.created_at).label("date"),
            func.count().label("count"),
        ).where(SysUser.created_at >= week_ago)
        .group_by(func.date(SysUser.created_at))
    )).all()
    user_trend = {str(r[0]): r[1] for r in user_trend_rows}

    inst_trend_rows = (await db.execute(
        select(
            func.date(AgentInstance.created_at).label("date"),
            func.count().label("count"),
        ).where(
            AgentInstance.created_at >= week_ago,
            AgentInstance.status != "deleted",
        ).group_by(func.date(AgentInstance.created_at))
    )).all()
    inst_trend = {str(r[0]): r[1] for r in inst_trend_rows}

    activity_trend = []
    for i in range(7):
        d = (today - timedelta(days=6 - i)).strftime("%Y-%m-%d")
        activity_trend.append({
            "date": d,
            "users": user_trend.get(d, 0),
            "instances": inst_trend.get(d, 0),
        })

    # --- Model usage ---
    model_rows = (await db.execute(
        select(
            InstanceModelConfig.model_name,
            func.count(Conversation.id).label("count"),
        ).join(Conversation, Conversation.instance_id == InstanceModelConfig.instance_id)
        .group_by(InstanceModelConfig.model_name)
        .order_by(func.count(Conversation.id).desc())
        .limit(5)
    )).all()
    total_conv = sum(r[1] for r in model_rows) or 1
    model_usage = [
        {"model": r[0] or "unknown", "count": r[1], "percentage": round(r[1] / total_conv * 100, 1)}
        for r in model_rows
    ]

    # --- Recent logs ---
    log_rows = (await db.execute(
        select(SysOperationLog).order_by(SysOperationLog.created_at.desc()).limit(10)
    )).scalars().all()

    recent_logs = [{
        "username": "",
        "user_id": log.user_id,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    } for log in log_rows]

    # Fill usernames
    user_ids = {log["user_id"] for log in recent_logs if log["user_id"]}
    if user_ids:
        users = (await db.execute(
            select(SysUser.id, SysUser.username).where(SysUser.id.in_(user_ids))
        )).all()
        user_map = {u[0]: u[1] for u in users}
        for log in recent_logs:
            log["username"] = user_map.get(log["user_id"], "")

    return success({
        "stats": {
            "user_count": user_total,
            "user_new_this_week": user_new_week,
            "instance_total": instance_total,
            "instance_new_this_week": instance_new_week,
            "instance_running": instance_running,
            "conversation_today": conv_today,
            "conversation_yesterday": conv_yesterday,
        },
        "instance_status": instance_status,
        "token_trend": token_trend,
        "activity_trend": activity_trend,
        "model_usage": model_usage,
        "recent_logs": recent_logs,
    })
