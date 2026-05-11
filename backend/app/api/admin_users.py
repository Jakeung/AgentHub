import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db
from app.models.user import SysUser
from app.models.role import SysRole
from app.models.instance import AgentInstance
from app.services.auth_service import hash_password
from app.services import instance_service
from app.core.response import success, page_data, get_client_ip
from app.core.exceptions import BusinessError
from app.services.audit_service import log_operation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


def _user_to_dict(u: SysUser, role_name: str | None = None) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "name": u.name or "",
        "email": u.email or "",
        "role_id": u.role_id,
        "role_name": role_name or "",
        "status": u.status,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("")
async def list_users(
    request: Request,
    status: str | None = None,
    role_id: int | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(SysUser)

    if status:
        query = query.where(SysUser.status == status)
    if role_id:
        query = query.where(SysUser.role_id == role_id)
    if keyword:
        query = query.where(
            SysUser.username.contains(keyword) | SysUser.name.contains(keyword)
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(SysUser.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    # Get role names
    role_ids = {u.role_id for u in users}
    roles = {}
    if role_ids:
        role_result = await db.execute(
            select(SysRole.id, SysRole.name).where(SysRole.id.in_(role_ids))
        )
        roles = {r[0]: r[1] for r in role_result.all()}

    items = [_user_to_dict(u, roles.get(u.role_id)) for u in users]
    return page_data(items, total, page, page_size)


class CreateUserReq(BaseModel):
    username: str
    password: str
    name: str = ""
    email: str = ""
    role_id: int = 2


@router.post("")
async def create_user(
    request: Request,
    req: CreateUserReq,
    db: AsyncSession = Depends(get_db),
):
    if len(req.username) < 3:
        raise BusinessError(-4, "用户名至少3位")
    if len(req.password) < 8:
        raise BusinessError(-4, "密码至少8位")

    dup = await db.execute(select(SysUser).where(SysUser.username == req.username))
    if dup.scalar_one_or_none():
        raise BusinessError(-4, "用户名已存在")

    if req.email:
        dup_email = await db.execute(select(SysUser).where(SysUser.email == req.email))
        if dup_email.scalar_one_or_none():
            raise BusinessError(-4, "邮箱已被使用")

    role = await db.execute(select(SysRole).where(SysRole.id == req.role_id))
    if not role.scalar_one_or_none():
        raise BusinessError(-4, "角色不存在")

    user = SysUser(
        username=req.username,
        password_hash=hash_password(req.password),
        name=req.name,
        email=req.email,
        role_id=req.role_id,
        status="active",
    )
    db.add(user)
    await db.flush()
    await log_operation(db, user_id=request.state.user_id, action="admin:user:create", target_type="user", target_id=user.id, detail={"username": req.username, "role_id": req.role_id}, ip_address=get_client_ip(request))
    await db.commit()

    role_result = await db.execute(select(SysRole.name).where(SysRole.id == user.role_id))
    role_name = role_result.scalar() or ""
    return success(_user_to_dict(user, role_name))


class UpdateUserReq(BaseModel):
    name: str | None = None
    email: str | None = None
    role_id: int | None = None
    status: str | None = None


@router.put("/{user_id}")
async def update_user(
    request: Request,
    user_id: int,
    req: UpdateUserReq,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user(db, user_id)

    # Prevent disabling self
    if req.status and req.status != "active" and user_id == request.state.user_id:
        raise BusinessError(-4, "不能禁用自己")

    # Prevent disabling other admins
    if req.status and req.status != "active" and user.role_id == 1:
        raise BusinessError(-4, "不能禁用管理员账号")

    if req.name is not None:
        user.name = req.name
    if req.email is not None:
        # Check email uniqueness
        if req.email:
            dup = await db.execute(
                select(SysUser).where(SysUser.email == req.email, SysUser.id != user_id)
            )
            if dup.scalar_one_or_none():
                raise BusinessError(-4, "邮箱已被使用")
        user.email = req.email
    if req.role_id is not None:
        # Validate role exists
        role = await db.execute(select(SysRole).where(SysRole.id == req.role_id))
        if not role.scalar_one_or_none():
            raise BusinessError(-4, "角色不存在")
        user.role_id = req.role_id
    if req.status is not None:
        if req.status not in ("active", "disabled"):
            raise BusinessError(-4, "状态无效")
        user.status = req.status

        if req.status == "disabled":
            result = await db.execute(
                select(AgentInstance).where(
                    AgentInstance.owner_user_id == user_id,
                    AgentInstance.status == "running",
                )
            )
            running_instances = result.scalars().all()
            for inst in running_instances:
                try:
                    await instance_service.stop_instance(db, inst)
                    await log_operation(db, user_id=request.state.user_id, action="admin:instance:stop", target_type="instance", target_id=inst.id, detail={"reason": "user_disabled"}, ip_address=get_client_ip(request))
                except Exception as e:
                    logger.warning(f"Failed to stop instance {inst.id} for disabled user {user_id}: {e}")

    await log_operation(db, user_id=request.state.user_id, action="admin:user:update", target_type="user", target_id=user_id, detail=req.model_dump(exclude_none=True), ip_address=get_client_ip(request))
    await db.commit()
    await db.refresh(user)

    # Get role name
    role_result = await db.execute(
        select(SysRole.name).where(SysRole.id == user.role_id)
    )
    role_name = role_result.scalar() or ""
    return success(_user_to_dict(user, role_name))


class ResetPasswordReq(BaseModel):
    new_password: str


@router.put("/{user_id}/password")
async def reset_password(
    request: Request,
    user_id: int,
    req: ResetPasswordReq,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user(db, user_id)
    if len(req.new_password) < 8:
        raise BusinessError(-4, "密码至少8位")
    user.password_hash = hash_password(req.new_password)
    await log_operation(db, user_id=request.state.user_id, action="admin:user:reset_password", target_type="user", target_id=user_id, ip_address=get_client_ip(request))
    await db.commit()
    return success(None)


@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user(db, user_id)

    if user_id == request.state.user_id:
        raise BusinessError(-4, "不能删除自己")
    if user.role_id == 1:
        raise BusinessError(-4, "不能删除管理员账号")

    await log_operation(db, user_id=request.state.user_id, action="admin:user:delete", target_type="user", target_id=user_id, detail={"username": user.username}, ip_address=get_client_ip(request))
    await db.delete(user)
    await db.commit()
    return success(None)


async def _get_user(db: AsyncSession, user_id: int) -> SysUser:
    result = await db.execute(select(SysUser).where(SysUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise BusinessError(-4, "用户不存在")
    return user
