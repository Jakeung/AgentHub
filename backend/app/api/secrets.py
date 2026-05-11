"""User secrets (API keys) management API."""
import httpx
import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db
from app.models.secret import ApiSecret
from app.services.secret_service import encrypt_key, key_suffix, mask_key, decrypt_key
from app.core.response import success, page_data, get_client_ip
from app.core.exceptions import BusinessError
from app.services.audit_service import log_operation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


class CreateSecretReq(BaseModel):
    name: str
    provider: str
    model_name: str = ""
    api_key: str


class UpdateSecretReq(BaseModel):
    name: str | None = None
    provider: str | None = None
    model_name: str | None = None
    api_key: str | None = None


def _secret_to_dict(s: ApiSecret) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "provider": s.provider,
        "model_name": s.model_name or "",
        "is_active": bool(s.is_active),
        "key_suffix": s.key_suffix,
        "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("")
async def list_secrets(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    query = select(ApiSecret).where(ApiSecret.owner_user_id == user_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(ApiSecret.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    items = [_secret_to_dict(s) for s in result.scalars().all()]
    return page_data(items, total, page, page_size)


@router.post("")
async def create_secret(
    request: Request,
    req: CreateSecretReq,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    secret = ApiSecret(
        name=req.name,
        provider=req.provider,
        model_name=req.model_name,
        encrypted_key=encrypt_key(req.api_key),
        key_suffix=key_suffix(req.api_key),
        owner_user_id=user_id,
    )
    db.add(secret)
    await db.flush()
    await log_operation(db, user_id=user_id, action="secret:create", target_type="secret", target_id=secret.id, detail={"name": req.name, "provider": req.provider}, ip_address=get_client_ip(request))
    await db.commit()
    await db.refresh(secret)
    return success(_secret_to_dict(secret))


@router.put("/{secret_id}")
async def update_secret(
    request: Request,
    secret_id: int,
    req: UpdateSecretReq,
    db: AsyncSession = Depends(get_db),
):
    secret = await _get_user_secret(db, secret_id, request.state.user_id)
    if req.name is not None:
        secret.name = req.name
    if req.provider is not None:
        secret.provider = req.provider
    if req.model_name is not None:
        secret.model_name = req.model_name
    if req.api_key is not None:
        secret.encrypted_key = encrypt_key(req.api_key)
        secret.key_suffix = key_suffix(req.api_key)
    await log_operation(db, user_id=request.state.user_id, action="secret:update", target_type="secret", target_id=secret_id, detail={"name": secret.name, "provider": secret.provider}, ip_address=get_client_ip(request))
    await db.commit()
    await db.refresh(secret)
    return success(_secret_to_dict(secret))


@router.delete("/{secret_id}")
async def delete_secret(
    request: Request,
    secret_id: int,
    db: AsyncSession = Depends(get_db),
):
    secret = await _get_user_secret(db, secret_id, request.state.user_id)
    name = secret.name
    await db.delete(secret)
    await log_operation(db, user_id=request.state.user_id, action="secret:delete", target_type="secret", target_id=secret_id, detail={"name": name}, ip_address=get_client_ip(request))
    await db.commit()
    return success(None)


@router.post("/{secret_id}/activate")
async def activate_secret(
    request: Request,
    secret_id: int,
    db: AsyncSession = Depends(get_db),
):
    user_id = request.state.user_id
    # Deactivate all
    all_q = select(ApiSecret).where(ApiSecret.owner_user_id == user_id)
    result = await db.execute(all_q)
    for s in result.scalars().all():
        s.is_active = False
    # Activate selected
    secret = await _get_user_secret(db, secret_id, user_id)
    secret.is_active = True
    await db.commit()

    # Update instance config with the new key
    from app.models.instance import AgentInstance
    from app.services.instance_service import update_instance_llm_config
    inst_result = await db.execute(
        select(AgentInstance).where(AgentInstance.owner_user_id == user_id, AgentInstance.status != "deleted")
    )
    instances = inst_result.scalars().all()
    if instances:
        api_key = decrypt_key(secret.encrypted_key)
        base_url = PROVIDER_BASE_URLS.get(secret.provider, "")
        for inst in instances:
            await update_instance_llm_config(db, inst, secret.provider, api_key, secret.model_name or "", base_url)

    return success(None)


async def _get_user_secret(
    db: AsyncSession, secret_id: int, user_id: int
) -> ApiSecret:
    result = await db.execute(
        select(ApiSecret).where(
            ApiSecret.id == secret_id,
            ApiSecret.owner_user_id == user_id,
        )
    )
    secret = result.scalar_one_or_none()
    if not secret:
        raise BusinessError(-4, "密钥不存在")
    return secret


# Provider base URLs for /v1/models
PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "openai": "https://api.openai.com",
    "anthropic": "https://api.anthropic.com",
    "openrouter": "https://openrouter.ai/api",
}


@router.get("/available-models")
async def list_available_models(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List models available from the active provider's /v1/models endpoint."""
    user_id = request.state.user_id

    # Check for active user secret
    result = await db.execute(
        select(ApiSecret).where(ApiSecret.owner_user_id == user_id, ApiSecret.is_active == True)
    )
    active_secret = result.scalar_one_or_none()

    if active_secret:
        api_key = decrypt_key(active_secret.encrypted_key)
        base_url = PROVIDER_BASE_URLS.get(active_secret.provider, "")
        if not base_url:
            return success([])
    else:
        # Use system default
        from app.api.admin_settings import get_setting
        provider = await get_setting(db, "hermes_llm_provider") or ""
        api_key_val = await get_setting(db, "hermes_llm_api_key") or ""
        base_url_val = await get_setting(db, "hermes_llm_base_url") or ""
        if not api_key_val:
            return success([])
        api_key = api_key_val
        # Determine base_url
        base_url = base_url_val.rstrip("/").replace("/v1", "") if base_url_val else PROVIDER_BASE_URLS.get(provider, "")
        if not base_url:
            return success([])

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{base_url}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                models = [m["id"] for m in data.get("data", [])]
                return success(models)
            return success([])
    except Exception as e:
        logger.warning(f"Failed to fetch models from {base_url}: {e}")
        return success([])
