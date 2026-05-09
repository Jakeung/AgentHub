"""Admin instance management API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db
from app.models.instance import AgentInstance
from app.models.user import SysUser
from app.services import instance_service
from app.core.response import success, page_data, get_client_ip
from app.core.exceptions import BusinessError
from app.api.instances import _instance_to_dict
from app.services.audit_service import log_operation

router = APIRouter(prefix="/api/admin/instances", tags=["admin-instances"])


@router.get("")
async def list_all_instances(
    request: Request,
    status: str | None = None,
    owner_id: int | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all instances (admin view)."""
    query = select(AgentInstance).where(AgentInstance.status != "deleted")

    if status:
        query = query.where(AgentInstance.status == status)
    if owner_id:
        query = query.where(AgentInstance.owner_user_id == owner_id)
    if keyword:
        query = query.where(
            AgentInstance.name.contains(keyword)
            | AgentInstance.container_name.contains(keyword)
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(AgentInstance.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    instances = result.scalars().all()

    # Enrich with owner username
    owner_ids = {inst.owner_user_id for inst in instances}
    owners = {}
    if owner_ids:
        owner_result = await db.execute(
            select(SysUser.id, SysUser.username).where(SysUser.id.in_(owner_ids))
        )
        owners = {row[0]: row[1] for row in owner_result.all()}

    items = []
    for inst in instances:
        d = _instance_to_dict(inst)
        d["owner_username"] = owners.get(inst.owner_user_id, "unknown")
        d["owner_user_id"] = inst.owner_user_id
        items.append(d)

    return page_data(items, total, page, page_size)


@router.get("/{instance_id}")
async def get_instance_detail(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_instance(db, instance_id)
    d = _instance_to_dict(instance, mask_env=False)

    # Get owner info
    owner = await db.execute(
        select(SysUser.username).where(SysUser.id == instance.owner_user_id)
    )
    d["owner_username"] = owner.scalar() or "unknown"
    d["owner_user_id"] = instance.owner_user_id
    return success(d)



@router.post("/{instance_id}/start")
async def admin_start_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_instance(db, instance_id)
    await instance_service.start_instance(db, instance)
    await log_operation(db, user_id=request.state.user_id, action="admin:instance:start", target_type="instance", target_id=instance_id, ip_address=get_client_ip(request))
    await db.commit()
    return success({"status": instance.status})


@router.post("/{instance_id}/stop")
async def admin_stop_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_instance(db, instance_id)
    await instance_service.stop_instance(db, instance)
    await log_operation(db, user_id=request.state.user_id, action="admin:instance:stop", target_type="instance", target_id=instance_id, ip_address=get_client_ip(request))
    await db.commit()
    return success({"status": instance.status})


@router.post("/{instance_id}/restart")
async def admin_restart_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_instance(db, instance_id)
    await instance_service.restart_instance(db, instance)
    await log_operation(db, user_id=request.state.user_id, action="admin:instance:restart", target_type="instance", target_id=instance_id, ip_address=get_client_ip(request))
    await db.commit()
    return success({"status": instance.status})


@router.delete("/{instance_id}")
async def admin_delete_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_instance(db, instance_id)
    await instance_service.delete_instance(db, instance)
    await log_operation(db, user_id=request.state.user_id, action="admin:instance:delete", target_type="instance", target_id=instance_id, ip_address=get_client_ip(request))
    await db.commit()
    return success(None)


@router.get("/{instance_id}/logs")
async def admin_get_logs(
    instance_id: int,
    tail: int = Query(default=200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_instance(db, instance_id)
    logs = instance_service.get_instance_logs(instance, tail=tail)
    return success({"logs": logs})


async def _get_instance(db: AsyncSession, instance_id: int) -> AgentInstance:
    result = await db.execute(
        select(AgentInstance).where(
            AgentInstance.id == instance_id,
            AgentInstance.status != "deleted",
        )
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise BusinessError(-4, "实例不存在")
    return instance
