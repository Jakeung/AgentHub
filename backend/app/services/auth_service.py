from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BusinessError
from app.models.user import SysUser
from app.models.role import SysRole, SysPermission, SysRolePermission

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(payload: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload["exp"] = expire
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


async def get_user_permissions(db: AsyncSession, role_id: int) -> list[str]:
    result = await db.execute(
        select(SysPermission.code)
        .join(SysRolePermission, SysRolePermission.permission_id == SysPermission.id)
        .where(SysRolePermission.role_id == role_id)
    )
    return [row[0] for row in result.all()]


async def get_user_with_role(db: AsyncSession, user_id: int) -> tuple[SysUser, str] | None:
    result = await db.execute(
        select(SysUser, SysRole.name)
        .join(SysRole, SysRole.id == SysUser.role_id)
        .where(SysUser.id == user_id)
    )
    row = result.first()
    return row if row else None
