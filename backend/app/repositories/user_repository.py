from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import SysUser
from app.models.role import SysRole, SysPermission, SysRolePermission
from .base import BaseRepository


class UserRepository(BaseRepository[SysUser]):
    """User repository for database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, SysUser)

    async def get_by_username(self, username: str) -> Optional[SysUser]:
        """Get user by username."""
        result = await self.db.execute(
            select(SysUser).where(SysUser.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_with_role(self, user_id: int) -> Optional[tuple[SysUser, str]]:
        """Get user with role name."""
        result = await self.db.execute(
            select(SysUser, SysRole.name)
            .join(SysRole, SysRole.id == SysUser.role_id)
            .where(SysUser.id == user_id)
        )
        row = result.first()
        return row if row else None

    async def get_user_permissions(self, role_id: int) -> list[str]:
        """Get user permissions by role ID."""
        result = await self.db.execute(
            select(SysPermission.code)
            .join(SysRolePermission, SysRolePermission.permission_id == SysPermission.id)
            .where(SysRolePermission.role_id == role_id)
        )
        return [row[0] for row in result.all()]
