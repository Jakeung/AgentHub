"""Admin system settings API — global configuration like default LLM keys."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
import httpx
import logging

from app.models.base import get_db
from app.models.system_setting import SystemSetting
from app.core.response import success, error, get_client_ip
from app.core.exceptions import BusinessError
from app.services.audit_service import log_operation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/settings", tags=["admin-settings"])

ALLOWED_SETTING_KEYS = {
    "hermes_llm_provider",
    "hermes_llm_model",
    "hermes_llm_api_key",
    "hermes_llm_base_url",
}


class SettingUpdate(BaseModel):
    key: str
    value: str
    description: str = ""


class SettingsBatch(BaseModel):
    settings: list[SettingUpdate] = Field(max_length=50)


@router.get("")
async def list_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    items = result.scalars().all()
    return success([
        {
            "id": s.id,
            "key": s.key,
            "value": _mask_value(s.key, s.value),
            "description": s.description,
        }
        for s in items
    ])


@router.put("")
async def update_settings(
    request: Request,
    req: SettingsBatch,
    db: AsyncSession = Depends(get_db),
):
    changed_keys = []
    for item in req.settings:
        if item.key not in ALLOWED_SETTING_KEYS:
            raise BusinessError(-4, f"不允许的设置项: {item.key}")
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == item.key)
        )
        existing = result.scalars().first()
        if existing:
            if not item.value.startswith("****"):
                existing.value = item.value
                changed_keys.append(item.key)
            if item.description:
                existing.description = item.description
        else:
            db.add(SystemSetting(
                key=item.key,
                value=item.value,
                description=item.description,
            ))
            changed_keys.append(item.key)
    if changed_keys:
        await log_operation(db, user_id=request.state.user_id, action="admin:settings:update", target_type="settings", detail={"keys": changed_keys}, ip_address=get_client_ip(request))
    await db.commit()
    return success(None)


def _mask_value(key: str, value: str) -> str:
    """Mask sensitive values like API keys."""
    if not value:
        return ""
    sensitive_keywords = ("key", "secret", "password", "token")
    if any(kw in key.lower() for kw in sensitive_keywords):
        if len(value) <= 4:
            return "****(" + str(len(value)) + ")"
        return "****" + value[-4:]
    return value


@router.post("/test")
async def test_llm_connection(db: AsyncSession = Depends(get_db)):
    provider = await get_setting(db, "hermes_llm_provider")
    api_key = await get_setting(db, "hermes_llm_api_key")
    base_url = await get_setting(db, "hermes_llm_base_url")
    model = await get_setting(db, "hermes_llm_model")

    if not api_key or not base_url:
        raise BusinessError(-1, "请先保存 API Key 和 Base URL")

    url = base_url.rstrip("/") + "/models"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            if resp.status_code == 200:
                data = resp.json()
                models = []
                if isinstance(data, dict) and "data" in data:
                    models = [m.get("id", "") for m in data["data"][:20]]
                return success({
                    "status": "ok",
                    "provider": provider or "",
                    "model": model or "",
                    "models_count": len(models),
                    "models": models,
                })
            elif resp.status_code == 401:
                raise BusinessError(-1, "API Key 无效或已过期")
            else:
                raise BusinessError(-1, f"API 返回错误: HTTP {resp.status_code}")
    except BusinessError:
        raise
    except httpx.TimeoutException:
        raise BusinessError(-1, "连接超时，请检查 Base URL 是否正确")
    except Exception as e:
        logger.warning(f"LLM connection test failed: {e}")
        raise BusinessError(-1, f"连接失败: {str(e)}")


# --- Internal helper for other services ---
async def get_setting(db: AsyncSession, key: str) -> str | None:
    result = await db.execute(
        select(SystemSetting.value).where(SystemSetting.key == key)
    )
    row = result.scalar_one_or_none()
    return row


# --- User-facing: get default model info (no secrets) ---
user_router = APIRouter(prefix="/api/settings", tags=["settings"])


@user_router.get("/default-model")
async def get_default_model(db: AsyncSession = Depends(get_db)):
    provider = await get_setting(db, "hermes_llm_provider") or ""
    model = await get_setting(db, "hermes_llm_model") or ""
    return success({"provider": provider, "model": model})
