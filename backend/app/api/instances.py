"""Instance management API - user endpoints."""
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db
from app.models.instance import AgentInstance
from app.schemas.instance import CreateInstanceRequest, UpdateInstanceRequest
from app.services import instance_service
from app.core.response import success, error, page_data, get_client_ip
from app.core.exceptions import BusinessError
from app.services.audit_service import log_operation

router = APIRouter(prefix="/api/instances", tags=["instances"])


def _mask_env(env_config_str: str) -> dict:
    """Mask sensitive values in env_config for API response."""
    try:
        env = json.loads(env_config_str) if env_config_str else {}
    except json.JSONDecodeError:
        return {}
    masked = {}
    for k, v in env.items():
        if "KEY" in k.upper() or "SECRET" in k.upper() or "TOKEN" in k.upper():
            masked[k] = v[:4] + "****" + v[-4:] if len(v) > 8 else "****"
        else:
            masked[k] = v
    return masked


def _instance_to_dict(inst: AgentInstance, mask_env: bool = True) -> dict:
    env = _mask_env(inst.env_config) if mask_env else json.loads(inst.env_config or "{}")
    return {
        "id": inst.id,
        "name": inst.name,
        "container_name": inst.container_name,
        "port": inst.port,
        "status": inst.status,
        "health_status": inst.health_status,
        "cpu_limit": inst.cpu_limit,
        "memory_limit_mb": inst.memory_limit_mb,
        "data_dir": inst.data_dir,
        "env_config": env,
        "created_at": inst.created_at.isoformat() if inst.created_at else None,
        "updated_at": inst.updated_at.isoformat() if inst.updated_at else None,
    }


@router.get("")
async def list_instances(
    request: Request,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    query = select(AgentInstance).where(
        AgentInstance.owner_user_id == user_id,
        AgentInstance.status != "deleted",
    )
    if status:
        query = query.where(AgentInstance.status == status)

    # Count
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total = (await db.execute(count_query)).scalar() or 0

    # Page
    query = query.order_by(AgentInstance.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = [_instance_to_dict(inst) for inst in result.scalars().all()]

    return page_data(items, total, page, page_size)


@router.post("")
async def create_instance(
    request: Request,
    req: CreateInstanceRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    username = request.state.username

    try:
        instance = await instance_service.create_instance(
            db=db,
            user_id=user_id,
            username=username,
            name=req.name,
            cpu_limit=req.cpu_limit,
            memory_limit_mb=req.memory_limit_mb,
            env_config=req.env_config,
        )
    except ValueError as e:
        return error(-1, str(e))
    await log_operation(db, user_id=user_id, action="instance:create", target_type="instance", target_id=instance.id, detail={"name": req.name}, ip_address=get_client_ip(request))
    await db.commit()
    return success(_instance_to_dict(instance))


@router.get("/upgrade-available")
async def check_upgrade_available(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    await instance_service.load_local_images()

    result = await db.execute(
        select(AgentInstance).where(
            AgentInstance.owner_user_id == user_id,
            AgentInstance.status != "deleted",
        )
    )
    instances = result.scalars().all()

    upgrade_info = {}
    for inst in instances:
        upgrade_info[inst.id] = instance_service.check_upgrade_available(inst)

    return success(upgrade_info)


@router.get("/{instance_id}")
async def get_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    return success(_instance_to_dict(instance))


@router.put("/{instance_id}")
async def update_instance(
    request: Request,
    instance_id: int,
    req: UpdateInstanceRequest,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)

    if req.name is not None:
        instance.name = req.name
    if req.cpu_limit is not None:
        instance.cpu_limit = req.cpu_limit
    if req.memory_limit_mb is not None:
        instance.memory_limit_mb = req.memory_limit_mb
    if req.env_config is not None:
        instance.env_config = json.dumps(req.env_config, ensure_ascii=False)

    await db.commit()
    await db.refresh(instance)
    return success(_instance_to_dict(instance))


@router.delete("/{instance_id}")
async def delete_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    name = instance.name
    await instance_service.delete_instance(db, instance)
    await log_operation(db, user_id=request.state.user_id, action="instance:delete", target_type="instance", target_id=instance_id, detail={"name": name}, ip_address=get_client_ip(request))
    await db.commit()
    return success(None)


@router.post("/{instance_id}/start")
async def start_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    await instance_service.start_instance(db, instance)
    await log_operation(db, user_id=request.state.user_id, action="instance:start", target_type="instance", target_id=instance_id, ip_address=get_client_ip(request))
    await db.commit()
    return success({"status": instance.status})


@router.post("/{instance_id}/stop")
async def stop_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    await instance_service.stop_instance(db, instance)
    await log_operation(db, user_id=request.state.user_id, action="instance:stop", target_type="instance", target_id=instance_id, ip_address=get_client_ip(request))
    await db.commit()
    return success({"status": instance.status})


@router.post("/{instance_id}/restart")
async def restart_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    await instance_service.restart_instance(db, instance)
    await log_operation(db, user_id=request.state.user_id, action="instance:restart", target_type="instance", target_id=instance_id, ip_address=get_client_ip(request))
    await db.commit()
    return success({"status": instance.status})


@router.post("/{instance_id}/upgrade")
async def upgrade_instance(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    was_running = await instance_service.upgrade_instance(db, instance)
    await log_operation(db, user_id=request.state.user_id, action="instance:upgrade", target_type="instance", target_id=instance_id, ip_address=get_client_ip(request))
    await db.commit()
    return success({"status": instance.status, "was_running": was_running})


@router.get("/{instance_id}/logs")
async def get_logs(
    request: Request,
    instance_id: int,
    tail: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    logs = instance_service.get_instance_logs(instance, tail=tail)
    return success({"logs": logs})


@router.get("/{instance_id}/stats")
async def get_stats(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    stats = instance_service.get_instance_stats(instance)
    if stats is None:
        return error(-1, "实例未运行，无法获取资源统计")
    return success(stats)


async def _get_user_instance(
    db: AsyncSession, instance_id: int, user_id: int
) -> AgentInstance:
    result = await db.execute(
        select(AgentInstance).where(
            AgentInstance.id == instance_id,
            AgentInstance.owner_user_id == user_id,
            AgentInstance.status != "deleted",
        )
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise BusinessError(-4, "实例不存在")
    return instance
