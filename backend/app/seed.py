"""Seed initial data: roles, permissions, role-permission bindings, admin user."""
import asyncio
from sqlalchemy import select, text
from app.models.base import engine, async_session, Base
from app.models.role import SysRole, SysPermission, SysRolePermission
from app.models.user import SysUser
from app.models.instance import AgentInstance, InstanceModelConfig
from app.models.secret import ApiSecret
from app.models.channel import InstanceChannelConfig
from app.models.audit import SysOperationLog, InstanceRuntimeLog
from app.models.task import AsyncTask
from app.models.conversation import Conversation, Message
from app.models.system_setting import SystemSetting
from app.models.invitation import InvitationCode
from app.services.auth_service import hash_password


async def _migrate_remove_unique_constraints(conn):
    """Remove UNIQUE constraints from agent_instance.port and container_name for soft-delete compatibility."""
    result = await conn.execute(text(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='agent_instance'"
    ))
    row = result.first()
    if not row or not row[0]:
        return
    create_sql = row[0]
    if "UNIQUE" not in create_sql:
        return

    print("🔄 Migrating agent_instance: removing UNIQUE constraints...")
    await conn.execute(text("ALTER TABLE agent_instance RENAME TO _agent_instance_old"))
    new_sql = create_sql.replace('"container_name" VARCHAR(200) NOT NULL UNIQUE', '"container_name" VARCHAR(200) NOT NULL')
    new_sql = new_sql.replace('"port" INTEGER NOT NULL UNIQUE', '"port" INTEGER NOT NULL')
    new_sql = new_sql.replace("container_name VARCHAR(200) NOT NULL UNIQUE", "container_name VARCHAR(200) NOT NULL")
    new_sql = new_sql.replace("port INTEGER NOT NULL UNIQUE", "port INTEGER NOT NULL")
    await conn.execute(text(new_sql))
    await conn.execute(text(
        "INSERT INTO agent_instance SELECT * FROM _agent_instance_old"
    ))
    await conn.execute(text("DROP TABLE _agent_instance_old"))
    print("✅ Migration complete: UNIQUE constraints removed")

ROLES = [
    {"id": 1, "name": "admin", "description": "系统管理员"},
    {"id": 2, "name": "user", "description": "普通用户"},
]

PERMISSIONS = [
    {"id": 1,  "code": "instance:view",  "name": "查看实例", "module": "instance"},
    {"id": 2,  "code": "instance:edit",  "name": "编辑实例", "module": "instance"},
    {"id": 3,  "code": "instance:delete","name": "删除实例", "module": "instance"},
    {"id": 4,  "code": "chat:use",       "name": "使用对话", "module": "chat"},
    {"id": 5,  "code": "channel:view",   "name": "查看渠道", "module": "channel"},
    {"id": 6,  "code": "channel:edit",   "name": "编辑渠道", "module": "channel"},
    {"id": 7,  "code": "apikey:view",    "name": "查看密钥", "module": "apikey"},
    {"id": 8,  "code": "apikey:edit",    "name": "编辑密钥", "module": "apikey"},
    {"id": 9,  "code": "admin:view",     "name": "查看管理", "module": "admin"},
    {"id": 10, "code": "admin:edit",     "name": "编辑管理", "module": "admin"},
    {"id": 11, "code": "audit:view",     "name": "查看审计", "module": "audit"},
    {"id": 12, "code": "monitor:view",   "name": "查看监控", "module": "monitor"},
]

# admin gets all 12, user gets 1-8
ROLE_PERMISSIONS = (
    [(1, pid) for pid in range(1, 13)]
    + [(2, pid) for pid in range(1, 9)]
)


async def seed():
    async with engine.begin() as conn:
        await _migrate_remove_unique_constraints(conn)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # Roles
        for r in ROLES:
            existing = await db.execute(select(SysRole).where(SysRole.id == r["id"]))
            if not existing.scalar_one_or_none():
                db.add(SysRole(**r))

        # Permissions
        for p in PERMISSIONS:
            existing = await db.execute(select(SysPermission).where(SysPermission.id == p["id"]))
            if not existing.scalar_one_or_none():
                db.add(SysPermission(**p))

        await db.commit()

        # Role-permission bindings
        for role_id, perm_id in ROLE_PERMISSIONS:
            existing = await db.execute(
                select(SysRolePermission).where(
                    SysRolePermission.role_id == role_id,
                    SysRolePermission.permission_id == perm_id,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(SysRolePermission(role_id=role_id, permission_id=perm_id))

        # Default admin user
        existing = await db.execute(select(SysUser).where(SysUser.username == "admin"))
        if not existing.scalar_one_or_none():
            db.add(SysUser(
                username="admin",
                password_hash=hash_password("admin123"),
                name="管理员",
                email="admin@agenthub.local",
                role_id=1,
                status="active",
            ))

        await db.commit()
        print("✅ Seed data initialized.")


if __name__ == "__main__":
    asyncio.run(seed())
