"""Channel configuration API — bind messaging platforms to Hermes instances."""
import json
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models.base import get_db
from app.models.channel import InstanceChannelConfig
from app.models.instance import AgentInstance
from app.services.secret_service import encrypt_key, decrypt_key
from app.core.response import success, error

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/channels", tags=["channels"])

# Supported platforms and their required config fields
# Each field maps to an env var name that Hermes reads
PLATFORM_SCHEMAS = {
    "telegram": {
        "label": "Telegram",
        "fields": [
            {"key": "TELEGRAM_BOT_TOKEN", "label": "Bot Token", "required": True, "secret": True, "placeholder": "从 @BotFather 获取"},
            {"key": "TELEGRAM_ALLOWED_USERS", "label": "允许的用户", "required": False, "secret": False, "placeholder": "逗号分隔的用户ID或用户名"},
        ],
    },
    "discord": {
        "label": "Discord",
        "fields": [
            {"key": "DISCORD_BOT_TOKEN", "label": "Bot Token", "required": True, "secret": True, "placeholder": "Discord Developer Portal 获取"},
        ],
    },
    "slack": {
        "label": "Slack",
        "fields": [
            {"key": "SLACK_BOT_TOKEN", "label": "Bot Token", "required": True, "secret": True, "placeholder": "xoxb-..."},
            {"key": "SLACK_APP_TOKEN", "label": "App Token", "required": True, "secret": True, "placeholder": "xapp-..."},
        ],
    },
    "weixin": {
        "label": "微信",
        "fields": [
            {"key": "WEIXIN_TOKEN", "label": "iLink Bot Token", "required": True, "secret": True, "placeholder": "通过 iLink 获取的 Bot Token"},
        ],
    },
    "wecom": {
        "label": "企业微信",
        "fields": [
            {"key": "WECOM_BOT_ID", "label": "Bot ID", "required": True, "secret": False, "placeholder": "企业微信机器人ID"},
            {"key": "WECOM_SECRET", "label": "Secret", "required": True, "secret": True, "placeholder": "企业微信机器人Secret"},
        ],
    },
    "feishu": {
        "label": "飞书",
        "fields": [
            {"key": "FEISHU_APP_ID", "label": "App ID", "required": True, "secret": False, "placeholder": "飞书开放平台获取"},
            {"key": "FEISHU_APP_SECRET", "label": "App Secret", "required": True, "secret": True, "placeholder": "飞书开放平台获取"},
            {"key": "FEISHU_VERIFICATION_TOKEN", "label": "Verification Token", "required": False, "secret": True, "placeholder": "事件订阅验证Token"},
        ],
    },
    "dingtalk": {
        "label": "钉钉",
        "fields": [
            {"key": "DINGTALK_CLIENT_ID", "label": "Client ID", "required": True, "secret": False, "placeholder": "钉钉开放平台 AppKey"},
            {"key": "DINGTALK_CLIENT_SECRET", "label": "Client Secret", "required": True, "secret": True, "placeholder": "钉钉开放平台 AppSecret"},
        ],
    },
    "qqbot": {
        "label": "QQ 机器人",
        "fields": [
            {"key": "QQ_APP_ID", "label": "App ID", "required": True, "secret": False, "placeholder": "QQ机器人平台获取"},
            {"key": "QQ_CLIENT_SECRET", "label": "Client Secret", "required": True, "secret": True, "placeholder": "QQ机器人平台获取"},
        ],
    },
}


class ChannelCreate(BaseModel):
    platform: str
    config: dict  # key→value pairs matching PLATFORM_SCHEMAS fields


class ChannelUpdate(BaseModel):
    config: dict


@router.get("/platforms")
async def list_platforms():
    """Return supported platforms and their config schemas."""
    return success(PLATFORM_SCHEMAS)


@router.get("")
async def list_channels(request: Request, db: AsyncSession = Depends(get_db)):
    """List all channel configs for the current user's instance."""
    user_id = request.state.user_id
    instance = await _get_user_instance(db, user_id)
    if not instance:
        return success([])

    result = await db.execute(
        select(InstanceChannelConfig).where(InstanceChannelConfig.instance_id == instance.id)
    )
    channels = result.scalars().all()
    return success([_channel_to_dict(ch) for ch in channels])


@router.post("")
async def create_channel(
    request: Request,
    req: ChannelCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new channel config."""
    user_id = request.state.user_id
    instance = await _get_user_instance(db, user_id)
    if not instance:
        return error(-1, "请先创建实例")

    if req.platform not in PLATFORM_SCHEMAS:
        return error(400, f"不支持的平台: {req.platform}")

    # Check duplicate
    existing = await db.execute(
        select(InstanceChannelConfig).where(
            InstanceChannelConfig.instance_id == instance.id,
            InstanceChannelConfig.platform == req.platform,
        )
    )
    if existing.scalar_one_or_none():
        return error(409, f"{PLATFORM_SCHEMAS[req.platform]['label']} 已配置，请编辑现有配置")

    # Validate required fields
    schema = PLATFORM_SCHEMAS[req.platform]
    for field in schema["fields"]:
        if field["required"] and not req.config.get(field["key"]):
            return error(400, f"缺少必填项: {field['label']}")

    # Encrypt the config
    encrypted = encrypt_key(json.dumps(req.config))
    channel = InstanceChannelConfig(
        instance_id=instance.id,
        platform=req.platform,
        config_encrypted=encrypted,
        status="active",
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    # Apply to container
    await _sync_channels_to_container(db, instance)

    return success(_channel_to_dict(channel))


@router.put("/{channel_id}")
async def update_channel(
    channel_id: int,
    request: Request,
    req: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a channel config."""
    user_id = request.state.user_id
    instance = await _get_user_instance(db, user_id)
    if not instance:
        return error(404, "实例不存在")

    result = await db.execute(
        select(InstanceChannelConfig).where(
            InstanceChannelConfig.id == channel_id,
            InstanceChannelConfig.instance_id == instance.id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        return error(404, "渠道配置不存在")

    # Merge: keep existing values for fields not provided
    existing_config = json.loads(decrypt_key(channel.config_encrypted))
    for k, v in req.config.items():
        if v:  # Only update non-empty values
            existing_config[k] = v

    channel.config_encrypted = encrypt_key(json.dumps(existing_config))
    await db.commit()

    await _sync_channels_to_container(db, instance)
    return success(_channel_to_dict(channel))


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete a channel config."""
    user_id = request.state.user_id
    instance = await _get_user_instance(db, user_id)
    if not instance:
        return error(404, "实例不存在")

    result = await db.execute(
        select(InstanceChannelConfig).where(
            InstanceChannelConfig.id == channel_id,
            InstanceChannelConfig.instance_id == instance.id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        return error(404, "渠道配置不存在")

    await db.delete(channel)
    await db.commit()

    await _sync_channels_to_container(db, instance)
    return success(None)


# --- Helpers ---

async def _get_user_instance(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(AgentInstance).where(AgentInstance.owner_user_id == user_id).limit(1)
    )
    return result.scalar_one_or_none()


def _channel_to_dict(ch: InstanceChannelConfig) -> dict:
    """Return channel info with masked secrets."""
    config = json.loads(decrypt_key(ch.config_encrypted))
    schema = PLATFORM_SCHEMAS.get(ch.platform, {})
    secret_keys = {f["key"] for f in schema.get("fields", []) if f.get("secret")}

    masked_config = {}
    for k, v in config.items():
        if k in secret_keys and v:
            masked_config[k] = "****" + v[-4:] if len(v) > 4 else "****"
        else:
            masked_config[k] = v

    return {
        "id": ch.id,
        "platform": ch.platform,
        "platform_label": schema.get("label", ch.platform),
        "config": masked_config,
        "status": ch.status,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
    }


async def _sync_channels_to_container(db: AsyncSession, instance: AgentInstance):
    """Rebuild the container .env with all channel env vars and restart."""
    from app.services.instance_service import update_instance_channels

    # Collect all channel configs for this instance
    result = await db.execute(
        select(InstanceChannelConfig).where(
            InstanceChannelConfig.instance_id == instance.id,
            InstanceChannelConfig.status == "active",
        )
    )
    channels = result.scalars().all()

    env_vars = {}
    for ch in channels:
        config = json.loads(decrypt_key(ch.config_encrypted))
        env_vars.update(config)

    await update_instance_channels(instance, env_vars)


# --- WeChat QR Login Flow ---
import httpx
import asyncio

ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
# In-memory store for active QR sessions: user_id -> session_data
_weixin_qr_sessions: dict[int, dict] = {}


@router.post("/weixin/qr-login")
async def weixin_qr_start(request: Request):
    """Start WeChat QR login: fetch QR code from iLink API."""
    user_id = request.state.user_id

    try:
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            resp = await client.get(
                f"{ILINK_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=3",
                headers={
                    "iLink-App-Id": "bot",
                    "iLink-App-ClientVersion": str((2 << 16) | (2 << 8) | 0),
                },
            )
            if resp.status_code != 200:
                return error(-1, f"获取二维码失败: HTTP {resp.status_code}")

            data = resp.json()
            qrcode_value = data.get("qrcode", "")
            qrcode_url = data.get("qrcode_img_content", "")

            if not qrcode_value:
                return error(-1, "获取二维码失败: 返回数据不完整")

            if qrcode_url and not qrcode_url.startswith(("http", "data:")):
                qrcode_url = f"data:image/png;base64,{qrcode_url}"

            # Store session
            _weixin_qr_sessions[user_id] = {
                "qrcode": qrcode_value,
                "base_url": ILINK_BASE_URL,
            }

            return success({
                "qr_url": qrcode_url or qrcode_value,
                "qrcode": qrcode_value,
            })
    except Exception as e:
        logger.error(f"WeChat QR login error: {e}")
        return error(-1, f"获取二维码失败: {str(e)[:100]}")


@router.get("/weixin/qr-status")
async def weixin_qr_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Poll WeChat QR login status."""
    user_id = request.state.user_id
    session = _weixin_qr_sessions.get(user_id)
    if not session:
        return error(-1, "没有进行中的扫码会话")

    qrcode = session["qrcode"]
    base_url = session["base_url"]

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.get(
                f"{base_url}/ilink/bot/get_qrcode_status?qrcode={qrcode}",
                headers={
                    "iLink-App-Id": "bot",
                    "iLink-App-ClientVersion": str((2 << 16) | (2 << 8) | 0),
                },
            )
            if resp.status_code != 200:
                return success({"status": "error", "message": f"HTTP {resp.status_code}"})

            data = resp.json()
            status = data.get("status", "wait")

            if status == "scaned_but_redirect":
                redirect_host = data.get("redirect_host", "")
                if redirect_host:
                    session["base_url"] = f"https://{redirect_host}"
                return success({"status": "scanned"})

            if status == "scaned":
                return success({"status": "scanned"})

            if status == "expired":
                _weixin_qr_sessions.pop(user_id, None)
                return success({"status": "expired"})

            if status == "confirmed":
                token = data.get("bot_token", "")
                account_id = data.get("ilink_bot_id", "")
                _weixin_qr_sessions.pop(user_id, None)

                if not token:
                    return error(-1, "扫码成功但未获取到 Token")

                # Auto-save as channel config
                instance = await _get_user_instance(db, user_id)
                if instance:
                    config_data = {"WEIXIN_TOKEN": token}
                    if account_id:
                        config_data["WEIXIN_ACCOUNT_ID"] = account_id

                    # Remove existing weixin config
                    existing = await db.execute(
                        select(InstanceChannelConfig).where(
                            InstanceChannelConfig.instance_id == instance.id,
                            InstanceChannelConfig.platform == "weixin",
                        )
                    )
                    old = existing.scalar_one_or_none()
                    if old:
                        await db.delete(old)

                    channel = InstanceChannelConfig(
                        instance_id=instance.id,
                        platform="weixin",
                        config_encrypted=encrypt_key(json.dumps(config_data)),
                        status="active",
                    )
                    db.add(channel)
                    await db.commit()
                    await _sync_channels_to_container(db, instance)

                return success({"status": "confirmed"})

            return success({"status": "waiting"})
    except Exception as e:
        logger.error(f"WeChat QR status error: {e}")
        return success({"status": "error", "message": str(e)[:100]})
