"""Tool management API — enable/disable Hermes toolsets per instance."""
import json
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db
from app.models.instance import AgentInstance
from app.models.tool import ToolRegistry, InstanceToolConfig
from app.services import instance_service
from app.core.response import success, error
from app.core.exceptions import BusinessError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/instances", tags=["tools"])


class ToolUpdateItem(BaseModel):
    tool_name: str
    enabled: bool
    config: dict | None = None


class ToolsUpdateRequest(BaseModel):
    tools: list[ToolUpdateItem]


@router.get("/{instance_id}/tools")
async def list_tools(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)

    registry_result = await db.execute(
        select(ToolRegistry).where(ToolRegistry.is_active == True).order_by(ToolRegistry.sort_order)
    )
    all_tools = registry_result.scalars().all()

    config_result = await db.execute(
        select(InstanceToolConfig).where(InstanceToolConfig.instance_id == instance.id)
    )
    configs = {c.tool_name: c for c in config_result.scalars().all()}

    tools = []
    for t in all_tools:
        cfg = configs.get(t.name)
        tools.append({
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "category": t.category,
            "icon": t.icon,
            "config_schema": json.loads(t.config_schema) if t.config_schema else {},
            "requires_api_key": t.requires_api_key,
            "enabled": cfg.enabled if cfg else False,
            "config": json.loads(cfg.config) if cfg and cfg.config else {},
        })

    return success(tools)


@router.put("/{instance_id}/tools")
async def update_tools(
    request: Request,
    instance_id: int,
    req: ToolsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)

    for item in req.tools:
        result = await db.execute(
            select(InstanceToolConfig).where(
                InstanceToolConfig.instance_id == instance.id,
                InstanceToolConfig.tool_name == item.tool_name,
            )
        )
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.enabled = item.enabled
            if item.config is not None:
                cfg.config = json.dumps(item.config, ensure_ascii=False)
        else:
            cfg = InstanceToolConfig(
                instance_id=instance.id,
                tool_name=item.tool_name,
                enabled=item.enabled,
                config=json.dumps(item.config or {}, ensure_ascii=False),
            )
            db.add(cfg)

    await db.commit()

    await _rewrite_config_and_restart(db, instance)

    return success(None)


async def _rewrite_config_and_restart(db: AsyncSession, instance: AgentInstance):
    """Rewrite config.yaml with platform_toolsets and restart if running."""
    from app.services.instance_service import write_hermes_config_with_tools
    await write_hermes_config_with_tools(db, instance)

    if instance.status == "running":
        try:
            from app.adapters.docker_adapter import DockerAdapter
            docker = DockerAdapter()
            docker.restart_container(instance.container_id)
        except Exception as e:
            logger.warning(f"Restart after tool config update failed: {e}")


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
