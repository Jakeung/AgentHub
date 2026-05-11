"""Admin invitation code management API."""
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db
from app.models.invitation import InvitationCode
from app.schemas.invitation import CreateInvitationReq, UpdateInvitationReq
from app.core.response import success, error, page_data, get_client_ip
from app.services.audit_service import log_operation

router = APIRouter(prefix="/api/admin/invitations", tags=["admin-invitations"])


def _invitation_to_dict(inv: InvitationCode) -> dict:
    return {
        "id": inv.id,
        "code": inv.code,
        "max_uses": inv.max_uses,
        "used_count": inv.used_count,
        "created_by": inv.created_by,
        "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        "is_active": inv.is_active,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


@router.get("")
async def list_invitations(
    request: Request,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(InvitationCode)
    if is_active is not None:
        query = query.where(InvitationCode.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(InvitationCode.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = [_invitation_to_dict(inv) for inv in result.scalars().all()]

    return page_data(items, total, page, page_size)


@router.post("")
async def create_invitations(
    request: Request,
    req: CreateInvitationReq,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    expires_at = None
    if req.expires_at:
        try:
            expires_at = datetime.fromisoformat(req.expires_at)
        except ValueError:
            return error(-1, "过期时间格式不正确")

    codes = []
    for _ in range(req.count):
        code = secrets.token_urlsafe(6)
        inv = InvitationCode(
            code=code,
            max_uses=req.max_uses,
            created_by=user_id,
            expires_at=expires_at,
        )
        db.add(inv)
        codes.append(code)

    await db.commit()
    await log_operation(
        db, user_id=user_id, action="admin:invitation:create",
        target_type="invitation", detail={"count": req.count},
        ip_address=get_client_ip(request),
    )
    await db.commit()

    return success({"codes": codes, "count": len(codes)})


@router.put("/{invitation_id}")
async def update_invitation(
    request: Request,
    invitation_id: int,
    req: UpdateInvitationReq,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InvitationCode).where(InvitationCode.id == invitation_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        return error(-4, "邀请码不存在")

    if req.is_active is not None:
        inv.is_active = req.is_active
    if req.max_uses is not None:
        inv.max_uses = req.max_uses

    await db.commit()
    await log_operation(
        db, user_id=request.state.user_id, action="admin:invitation:update",
        target_type="invitation", target_id=invitation_id,
        ip_address=get_client_ip(request),
    )
    await db.commit()

    return success(_invitation_to_dict(inv))


@router.delete("/{invitation_id}")
async def delete_invitation(
    request: Request,
    invitation_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InvitationCode).where(InvitationCode.id == invitation_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        return error(-4, "邀请码不存在")

    await db.delete(inv)
    await db.commit()
    await log_operation(
        db, user_id=request.state.user_id, action="admin:invitation:delete",
        target_type="invitation", target_id=invitation_id,
        ip_address=get_client_ip(request),
    )
    await db.commit()

    return success(None)
