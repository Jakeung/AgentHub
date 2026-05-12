"""User-facing usage statistics API."""
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.core.response import success
from app.services import usage_service

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/summary")
async def get_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    data = await usage_service.get_user_summary(db, request.state.user_id)
    return success(data)


@router.get("/trend")
async def get_trend(
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    data = await usage_service.get_user_trend(db, request.state.user_id, days=days)
    return success(data)
