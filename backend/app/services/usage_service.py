"""Usage statistics service: recording and querying token usage."""
import logging
from datetime import date, timedelta
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import DailyUsageStats, ModelPricing

logger = logging.getLogger(__name__)


async def record_usage(
    db: AsyncSession,
    user_id: int,
    instance_id: int,
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
):
    if prompt_tokens <= 0 and completion_tokens <= 0:
        return

    today = date.today()
    total = prompt_tokens + completion_tokens

    result = await db.execute(
        select(DailyUsageStats).where(
            DailyUsageStats.user_id == user_id,
            DailyUsageStats.instance_id == instance_id,
            DailyUsageStats.model_name == (model_name or ""),
            DailyUsageStats.date == today,
        )
    )
    row = result.scalar_one_or_none()

    if row:
        row.request_count = (row.request_count or 0) + 1
        row.prompt_tokens = (row.prompt_tokens or 0) + prompt_tokens
        row.completion_tokens = (row.completion_tokens or 0) + completion_tokens
        row.total_tokens = (row.total_tokens or 0) + total
    else:
        db.add(DailyUsageStats(
            user_id=user_id,
            instance_id=instance_id,
            model_name=model_name or "",
            date=today,
            request_count=1,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
        ))

    try:
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to record usage: {e}")
        await db.rollback()


async def _sum_usage(db: AsyncSession, user_id: int | None, start_date: date, end_date: date) -> dict:
    query = select(
        func.coalesce(func.sum(DailyUsageStats.request_count), 0).label("requests"),
        func.coalesce(func.sum(DailyUsageStats.prompt_tokens), 0).label("prompt_tokens"),
        func.coalesce(func.sum(DailyUsageStats.completion_tokens), 0).label("completion_tokens"),
        func.coalesce(func.sum(DailyUsageStats.total_tokens), 0).label("total_tokens"),
    ).where(
        DailyUsageStats.date >= start_date,
        DailyUsageStats.date <= end_date,
    )
    if user_id is not None:
        query = query.where(DailyUsageStats.user_id == user_id)

    row = (await db.execute(query)).one()
    return {
        "requests": row.requests,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "total_tokens": row.total_tokens,
    }


async def get_user_summary(db: AsyncSession, user_id: int) -> dict:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    today_stats = await _sum_usage(db, user_id, today, today)
    week_stats = await _sum_usage(db, user_id, week_start, today)
    month_stats = await _sum_usage(db, user_id, month_start, today)

    return {
        "today": today_stats,
        "this_week": week_stats,
        "this_month": month_stats,
    }


async def get_user_trend(db: AsyncSession, user_id: int, days: int = 30) -> list[dict]:
    start = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(
            DailyUsageStats.date,
            func.sum(DailyUsageStats.request_count).label("requests"),
            func.sum(DailyUsageStats.prompt_tokens).label("prompt_tokens"),
            func.sum(DailyUsageStats.completion_tokens).label("completion_tokens"),
            func.sum(DailyUsageStats.total_tokens).label("total_tokens"),
        )
        .where(DailyUsageStats.user_id == user_id, DailyUsageStats.date >= start)
        .group_by(DailyUsageStats.date)
        .order_by(DailyUsageStats.date)
    )
    return [
        {
            "date": str(r.date),
            "requests": r.requests or 0,
            "prompt_tokens": r.prompt_tokens or 0,
            "completion_tokens": r.completion_tokens or 0,
            "total_tokens": r.total_tokens or 0,
        }
        for r in result.all()
    ]


async def get_admin_overview(db: AsyncSession) -> dict:
    today = date.today()
    month_start = today.replace(day=1)

    month_stats = await _sum_usage(db, None, month_start, today)

    user_count_result = await db.execute(
        select(func.count(func.distinct(DailyUsageStats.user_id))).where(
            DailyUsageStats.date >= month_start
        )
    )
    active_users = user_count_result.scalar() or 0

    return {
        "this_month": month_stats,
        "active_users": active_users,
    }


async def get_admin_by_user(db: AsyncSession) -> list[dict]:
    from app.models.user import SysUser
    month_start = date.today().replace(day=1)

    result = await db.execute(
        select(
            DailyUsageStats.user_id,
            SysUser.username,
            SysUser.name,
            func.sum(DailyUsageStats.request_count).label("requests"),
            func.sum(DailyUsageStats.total_tokens).label("total_tokens"),
            func.sum(DailyUsageStats.prompt_tokens).label("prompt_tokens"),
            func.sum(DailyUsageStats.completion_tokens).label("completion_tokens"),
        )
        .join(SysUser, SysUser.id == DailyUsageStats.user_id)
        .where(DailyUsageStats.date >= month_start)
        .group_by(DailyUsageStats.user_id, SysUser.username, SysUser.name)
        .order_by(func.sum(DailyUsageStats.total_tokens).desc())
    )
    return [
        {
            "user_id": r.user_id,
            "username": r.username,
            "name": r.name,
            "requests": r.requests or 0,
            "total_tokens": r.total_tokens or 0,
            "prompt_tokens": r.prompt_tokens or 0,
            "completion_tokens": r.completion_tokens or 0,
        }
        for r in result.all()
    ]
