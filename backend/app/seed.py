"""Seed initial data: roles, permissions, role-permission bindings, admin user, tool registry."""
import asyncio
import json
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
from app.models.tool import ToolRegistry, InstanceToolConfig, InstanceSkillConfig
from app.models.usage import DailyUsageStats, ModelPricing
from app.services.auth_service import hash_password


async def _migrate_add_missing_columns(conn):
    """Add columns that exist in models but are missing from the database."""
    migrations = [
        ("message", "prompt_tokens", "INTEGER DEFAULT 0"),
        ("message", "completion_tokens", "INTEGER DEFAULT 0"),
    ]
    for table, column, col_type in migrations:
        try:
            result = await conn.execute(text(
                f"SELECT COUNT(*) FROM pragma_table_info('{table}') WHERE name='{column}'"
            ))
            if result.scalar() == 0:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                print(f"✅ Added column {table}.{column}")
        except Exception as e:
            print(f"⚠️ Migration {table}.{column} skipped: {e}")


async def _migrate_remove_unique_constraints(conn):
    """Remove UNIQUE constraints from agent_instance.port and container_name for soft-delete compatibility."""
    try:
        result = await conn.execute(text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='agent_instance'"
        ))
        row = result.first()
        if not row or not row[0]:
            return
        create_sql = row[0]
        has_port_unique = "port" in create_sql and "UNIQUE" in create_sql.split("port")[1].split(",")[0]
        if not has_port_unique:
            return

        print("🔄 Migrating agent_instance: removing UNIQUE constraints...")
        await conn.execute(text("ALTER TABLE agent_instance RENAME TO _agent_instance_old"))
        new_sql = create_sql.replace(" UNIQUE", "", 2)
        await conn.execute(text(new_sql))
        await conn.execute(text(
            "INSERT INTO agent_instance SELECT * FROM _agent_instance_old"
        ))
        await conn.execute(text("DROP TABLE _agent_instance_old"))
        print("✅ Migration complete: UNIQUE constraints removed")
    except Exception as e:
        print(f"⚠️ Migration skipped: {e}")

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

DEFAULT_TOOLS = [
    {
        "name": "web",
        "display_name": "网络搜索",
        "description": "网络搜索和网页内容提取（web_search + web_extract）",
        "category": "search",
        "icon": "search",
        "config_schema": json.dumps({
            "type": "object",
            "properties": {
                "WEB_BACKEND": {
                    "type": "string",
                    "title": "搜索引擎",
                    "description": "选择搜索后端",
                    "enum": ["tavily", "exa", "firecrawl", "parallel"],
                },
                "TAVILY_API_KEY": {
                    "type": "string",
                    "title": "Tavily API Key",
                    "description": "从 tavily.com 获取（1000次/月免费）",
                    "backend": "tavily",
                },
                "EXA_API_KEY": {
                    "type": "string",
                    "title": "Exa API Key",
                    "description": "从 exa.ai 获取（1000次/月免费）",
                    "backend": "exa",
                },
                "FIRECRAWL_API_KEY": {
                    "type": "string",
                    "title": "Firecrawl API Key",
                    "description": "从 firecrawl.dev 获取（500次/月免费）",
                    "backend": "firecrawl",
                },
                "PARALLEL_API_KEY": {
                    "type": "string",
                    "title": "Parallel API Key",
                    "description": "从 parallel.ai 获取",
                    "backend": "parallel",
                },
            },
            "required": ["WEB_BACKEND"],
        }),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": True,
        "sort_order": 1,
    },
    {
        "name": "terminal",
        "display_name": "终端执行",
        "description": "命令行执行和进程管理（terminal + process）",
        "category": "code",
        "icon": "terminal",
        "config_schema": json.dumps({"type": "object", "properties": {}}),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": False,
        "sort_order": 2,
    },
    {
        "name": "file",
        "display_name": "文件操作",
        "description": "文件读写、补丁、搜索（read_file + write_file + patch + search）",
        "category": "file",
        "icon": "folder",
        "config_schema": json.dumps({"type": "object", "properties": {}}),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": False,
        "sort_order": 3,
    },
    {
        "name": "browser",
        "display_name": "浏览器自动化",
        "description": "网页导航、截图、点击、输入等自动化操作",
        "category": "browser",
        "icon": "chrome",
        "config_schema": json.dumps({
            "type": "object",
            "properties": {
                "BROWSERBASE_API_KEY": {
                    "type": "string",
                    "title": "Browserbase API Key",
                    "description": "浏览器服务 API Key",
                }
            },
            "required": ["BROWSERBASE_API_KEY"],
        }),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": True,
        "sort_order": 4,
    },
    {
        "name": "vision",
        "display_name": "图像分析",
        "description": "分析和理解图片内容",
        "category": "vision",
        "icon": "eye",
        "config_schema": json.dumps({
            "type": "object",
            "properties": {
                "OPENROUTER_API_KEY": {
                    "type": "string",
                    "title": "OpenRouter API Key",
                    "description": "视觉分析需要 OpenRouter API",
                }
            },
        }),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": True,
        "sort_order": 5,
    },
    {
        "name": "image_gen",
        "display_name": "图像生成",
        "description": "使用 FLUX 模型生成图片",
        "category": "image",
        "icon": "image",
        "config_schema": json.dumps({
            "type": "object",
            "properties": {
                "FAL_KEY": {
                    "type": "string",
                    "title": "Fal.ai API Key",
                    "description": "图像生成需要 Fal.ai API Key",
                }
            },
            "required": ["FAL_KEY"],
        }),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": True,
        "sort_order": 6,
    },
    {
        "name": "tts",
        "display_name": "文本转语音",
        "description": "将文本转换为语音（支持 Edge TTS 免费方案）",
        "category": "media",
        "icon": "volume",
        "config_schema": json.dumps({"type": "object", "properties": {}}),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": False,
        "sort_order": 7,
    },
    {
        "name": "todo",
        "display_name": "任务规划",
        "description": "多步骤任务的规划和追踪",
        "category": "productivity",
        "icon": "check-square",
        "config_schema": json.dumps({"type": "object", "properties": {}}),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": False,
        "sort_order": 8,
    },
    {
        "name": "skills",
        "display_name": "技能系统",
        "description": "查看和加载技能文档，获取领域专业指导",
        "category": "system",
        "icon": "book",
        "config_schema": json.dumps({"type": "object", "properties": {}}),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": False,
        "sort_order": 9,
    },
    {
        "name": "cronjob",
        "display_name": "定时任务",
        "description": "创建和管理定时执行的自动化任务",
        "category": "automation",
        "icon": "clock",
        "config_schema": json.dumps({"type": "object", "properties": {}}),
        "default_config": json.dumps({}),
        "is_active": True,
        "requires_api_key": False,
        "sort_order": 10,
    },
]


async def seed():
    async with engine.begin() as conn:
        await _migrate_remove_unique_constraints(conn)
        await _migrate_add_missing_columns(conn)
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

        # Tool registry
        for t in DEFAULT_TOOLS:
            existing = await db.execute(
                select(ToolRegistry).where(ToolRegistry.name == t["name"])
            )
            if not existing.scalar_one_or_none():
                db.add(ToolRegistry(**t))

        # Default model pricing
        default_pricing = [
            {"model_name": "deepseek-chat", "provider": "deepseek", "input_price_per_1k": 0.001, "output_price_per_1k": 0.002, "currency": "CNY"},
        ]
        for p in default_pricing:
            existing = await db.execute(
                select(ModelPricing).where(ModelPricing.model_name == p["model_name"])
            )
            if not existing.scalar_one_or_none():
                db.add(ModelPricing(**p))

        await db.commit()
        print("✅ Seed data initialized.")


if __name__ == "__main__":
    asyncio.run(seed())
