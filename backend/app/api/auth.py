from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.base import get_db
from app.models.user import SysUser
from app.models.invitation import InvitationCode
from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_token,
    get_user_permissions,
    get_user_with_role,
)
from app.core.response import success, error, get_client_ip
from app.core.exceptions import BusinessError
from app.services.audit_service import log_operation

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Validate invitation code
    result = await db.execute(
        select(InvitationCode).where(InvitationCode.code == req.invitation_code)
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        return error(-1, "邀请码无效")
    if not invitation.is_active:
        return error(-1, "邀请码已停用")
    if invitation.used_count >= invitation.max_uses:
        return error(-1, "邀请码已用完")
    if invitation.expires_at and invitation.expires_at < datetime.now(timezone.utc):
        return error(-1, "邀请码已过期")

    # Check username uniqueness
    existing = await db.execute(select(SysUser).where(SysUser.username == req.username))
    if existing.scalar_one_or_none():
        return error(-1, "用户名已存在")

    # Check email uniqueness
    if req.email:
        existing = await db.execute(select(SysUser).where(SysUser.email == req.email))
        if existing.scalar_one_or_none():
            return error(-1, "邮箱已被注册")

    user = SysUser(
        username=req.username,
        password_hash=hash_password(req.password),
        name=req.username,
        email=req.email,
        role_id=2,
    )
    db.add(user)
    invitation.used_count += 1
    await db.commit()
    await db.refresh(user)

    return success({"id": user.id, "username": user.username, "email": user.email})


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SysUser).where(SysUser.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        return error(-1, "用户名或密码错误")

    if user.status != "active":
        return error(-1, "账号已被禁用")

    # Get role name and permissions
    user_role = await get_user_with_role(db, user.id)
    role_name = user_role[1] if user_role else "user"
    permissions = await get_user_permissions(db, user.role_id)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await log_operation(db, user_id=user.id, action="auth:login", target_type="user", target_id=user.id, detail={"username": user.username}, ip_address=get_client_ip(request))
    await db.commit()

    # Create JWT
    token = create_token({
        "id": user.id,
        "username": user.username,
        "role": role_name,
        "permissions": permissions,
    })

    response = JSONResponse(content=success({
        "user": {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "role": role_name,
        },
        "permissions": permissions,
    }))
    from app.core.config import get_settings
    settings = get_settings()
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key="auth-token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="strict",
        path="/",
        max_age=86400,
    )
    return response


@router.post("/logout")
async def logout():
    response = JSONResponse(content=success(None))
    response.delete_cookie(key="auth-token", path="/")
    return response


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.state.user_id
    user_role = await get_user_with_role(db, user_id)
    if not user_role:
        return error(-2, "用户不存在")

    user, role_name = user_role
    permissions = await get_user_permissions(db, user.role_id)

    return success({
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "email": user.email,
        "role": role_name,
        "permissions": permissions,
        "last_login_at": user.last_login_at,
    })
