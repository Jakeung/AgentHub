"""Skills management API — install/uninstall/toggle/custom skills."""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db
from app.models.instance import AgentInstance
from app.services import skill_service
from app.core.response import success, error
from app.core.exceptions import BusinessError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/instances", tags=["skills"])


class SkillInstallRequest(BaseModel):
    skill_name: str
    source: str  # builtin / optional


class SkillUninstallRequest(BaseModel):
    skill_name: str


class SkillToggleRequest(BaseModel):
    skill_name: str
    enabled: bool


class CustomSkillCreate(BaseModel):
    name: str
    display_name: str
    description: str = ""
    tags: list[str] = []
    content: str


class CustomSkillUpdate(BaseModel):
    skill_name: str
    display_name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    content: str | None = None


class CustomSkillDelete(BaseModel):
    skill_name: str


@router.get("/{instance_id}/skills")
async def list_skills(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    result = await skill_service.list_installed_skills(db, instance)
    return success(result)


@router.get("/{instance_id}/skills/available")
async def list_available_skills(
    request: Request,
    instance_id: int,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    result = await skill_service.list_available_skills(instance)
    return success(result)


@router.post("/{instance_id}/skills/install")
async def install_skill(
    request: Request,
    instance_id: int,
    req: SkillInstallRequest,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    await skill_service.install_skill(db, instance, req.skill_name, req.source)
    return success(None)


@router.post("/{instance_id}/skills/uninstall")
async def uninstall_skill(
    request: Request,
    instance_id: int,
    req: SkillUninstallRequest,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    await skill_service.uninstall_skill(db, instance, req.skill_name)
    return success(None)


@router.put("/{instance_id}/skills/toggle")
async def toggle_skill(
    request: Request,
    instance_id: int,
    req: SkillToggleRequest,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    await skill_service.toggle_skill(db, instance, req.skill_name, req.enabled)
    return success(None)


@router.post("/{instance_id}/skills/custom")
async def create_custom_skill(
    request: Request,
    instance_id: int,
    req: CustomSkillCreate,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    await skill_service.create_custom_skill(
        db, instance, req.name, req.display_name, req.description, req.tags, req.content,
    )
    return success(None)


@router.put("/{instance_id}/skills/custom")
async def update_custom_skill(
    request: Request,
    instance_id: int,
    req: CustomSkillUpdate,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    await skill_service.update_custom_skill(
        db, instance, req.skill_name, req.display_name, req.description, req.tags, req.content,
    )
    return success(None)


@router.delete("/{instance_id}/skills/custom")
async def delete_custom_skill(
    request: Request,
    instance_id: int,
    req: CustomSkillDelete,
    db: AsyncSession = Depends(get_db),
):
    instance = await _get_user_instance(db, instance_id, request.state.user_id)
    await skill_service.delete_custom_skill(db, instance, req.skill_name)
    return success(None)


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
