"""Admin tool registry management API."""
import json
from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.models.tool import ToolRegistry
from app.core.response import success, page_data, get_client_ip
from app.core.exceptions import BusinessError
from app.services.audit_service import log_operation

router = APIRouter(prefix="/api/admin/tools", tags=["admin-tools"])


class ToolCreateRequest(BaseModel):
    name: str
    display_name: str
    description: str = ""
    category: str = ""
    icon: str = ""
    config_schema: dict | None = None
    default_config: dict | None = None
    is_active: bool = True
    requires_api_key: bool = False
    sort_order: int = 0


class ToolUpdateRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    config_schema: dict | None = None
    default_config: dict | None = None
    is_active: bool | None = None
    requires_api_key: bool | None = None
    sort_order: int | None = None


@router.get("")
async def list_tools(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(ToolRegistry).order_by(ToolRegistry.sort_order)
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = [
        {
            "id": t.id,
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "category": t.category,
            "icon": t.icon,
            "config_schema": json.loads(t.config_schema) if t.config_schema else {},
            "default_config": json.loads(t.default_config) if t.default_config else {},
            "is_active": t.is_active,
            "requires_api_key": t.requires_api_key,
            "sort_order": t.sort_order,
        }
        for t in result.scalars().all()
    ]
    return page_data(items, total, page, page_size)


@router.post("")
async def create_tool(
    request: Request,
    req: ToolCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(ToolRegistry).where(ToolRegistry.name == req.name)
    )
    if existing.scalar_one_or_none():
        raise BusinessError(-1, f"工具 '{req.name}' 已存在")

    tool = ToolRegistry(
        name=req.name,
        display_name=req.display_name,
        description=req.description,
        category=req.category,
        icon=req.icon,
        config_schema=json.dumps(req.config_schema or {}, ensure_ascii=False),
        default_config=json.dumps(req.default_config or {}, ensure_ascii=False),
        is_active=req.is_active,
        requires_api_key=req.requires_api_key,
        sort_order=req.sort_order,
    )
    db.add(tool)
    await log_operation(
        db, user_id=request.state.user_id, action="admin:tool:create",
        target_type="tool", detail={"name": req.name},
        ip_address=get_client_ip(request),
    )
    await db.commit()
    return success({"id": tool.id, "name": tool.name})


@router.put("/{tool_id}")
async def update_tool(
    request: Request,
    tool_id: int,
    req: ToolUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ToolRegistry).where(ToolRegistry.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise BusinessError(-4, "工具不存在")

    updates = req.model_dump(exclude_none=True)
    for key in ("config_schema", "default_config"):
        if key in updates:
            updates[key] = json.dumps(updates[key], ensure_ascii=False)
    for key, value in updates.items():
        setattr(tool, key, value)

    await log_operation(
        db, user_id=request.state.user_id, action="admin:tool:update",
        target_type="tool", target_id=tool_id,
        detail={"name": tool.name, "updates": list(updates.keys())},
        ip_address=get_client_ip(request),
    )
    await db.commit()
    return success(None)


@router.delete("/{tool_id}")
async def delete_tool(
    request: Request,
    tool_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ToolRegistry).where(ToolRegistry.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise BusinessError(-4, "工具不存在")

    tool_name = tool.name
    await db.delete(tool)
    await log_operation(
        db, user_id=request.state.user_id, action="admin:tool:delete",
        target_type="tool", target_id=tool_id,
        detail={"name": tool_name},
        ip_address=get_client_ip(request),
    )
    await db.commit()
    return success(None)
