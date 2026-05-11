"""Skill service — install/uninstall/toggle/custom skills for Hermes instances."""
import os
import logging
import asyncio
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance import AgentInstance
from app.models.tool import InstanceSkillConfig
from app.adapters.docker_adapter import DockerAdapter
from app.core.exceptions import BusinessError

logger = logging.getLogger(__name__)


def _parse_skill_md(content: str) -> dict:
    """Parse YAML frontmatter from SKILL.md content."""
    if not content.startswith("---"):
        return {"name": "", "description": "", "tags": []}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {"name": "", "description": "", "tags": []}
    frontmatter = parts[1].strip()
    result = {"name": "", "description": "", "tags": []}
    for line in frontmatter.split("\n"):
        if line.startswith("name:"):
            result["name"] = line.split(":", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            result["description"] = line.split(":", 1)[1].strip().strip('"').strip("'")
        elif "tags:" in line and "[" in line:
            tags_str = line.split("[", 1)[1].split("]")[0]
            result["tags"] = [t.strip().strip('"').strip("'") for t in tags_str.split(",") if t.strip()]
    return result


async def list_installed_skills(
    db: AsyncSession,
    instance: AgentInstance,
) -> dict:
    """List skills installed in the instance data directory."""
    skills_dir = os.path.join(instance.data_dir, "skills")
    installed = []

    db_result = await db.execute(
        select(InstanceSkillConfig).where(InstanceSkillConfig.instance_id == instance.id)
    )
    db_configs = {c.skill_name: c for c in db_result.scalars().all()}

    if os.path.isdir(skills_dir):
        for entry in _walk_skills(skills_dir):
            skill_name = entry["name"]
            db_cfg = db_configs.get(skill_name)
            installed.append({
                "name": skill_name,
                "display_name": entry.get("display_name", skill_name),
                "description": entry.get("description", ""),
                "category": skill_name.split("/")[0] if "/" in skill_name else "custom",
                "source": db_cfg.source if db_cfg else "custom",
                "enabled": db_cfg.enabled if db_cfg else True,
                "tags": entry.get("tags", []),
            })

    disabled_dir = os.path.join(skills_dir, ".disabled")
    if os.path.isdir(disabled_dir):
        for entry in _walk_skills(disabled_dir):
            skill_name = entry["name"]
            installed.append({
                "name": skill_name,
                "display_name": entry.get("display_name", skill_name),
                "description": entry.get("description", ""),
                "category": skill_name.split("/")[0] if "/" in skill_name else "custom",
                "source": db_configs.get(skill_name, None) and db_configs[skill_name].source or "custom",
                "enabled": False,
                "tags": entry.get("tags", []),
            })

    enabled_count = sum(1 for s in installed if s["enabled"])
    custom_count = sum(1 for s in installed if s["source"] == "custom")

    return {
        "installed": installed,
        "stats": {
            "total_installed": len(installed),
            "enabled": enabled_count,
            "disabled": len(installed) - enabled_count,
            "custom": custom_count,
        },
    }


def _walk_skills(base_dir: str) -> list[dict]:
    """Walk a skills directory and parse SKILL.md files."""
    results = []
    if not os.path.isdir(base_dir):
        return results
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if "SKILL.md" in files:
            rel = os.path.relpath(root, base_dir)
            try:
                with open(os.path.join(root, "SKILL.md"), "r") as f:
                    content = f.read(4096)
                meta = _parse_skill_md(content)
                results.append({
                    "name": rel,
                    "display_name": meta.get("name") or rel.split("/")[-1],
                    "description": meta.get("description", ""),
                    "tags": meta.get("tags", []),
                })
            except Exception:
                results.append({"name": rel, "display_name": rel, "description": "", "tags": []})
    return results


async def list_available_skills(instance: AgentInstance) -> dict:
    """List skills available in the Hermes container's built-in/optional directories."""
    docker = DockerAdapter()
    status = docker.get_container_status(instance.container_id)
    if status != "running":
        raise BusinessError(-1, "实例必须处于运行状态才能查看可用技能")

    installed_names = set()
    skills_dir = os.path.join(instance.data_dir, "skills")
    if os.path.isdir(skills_dir):
        for entry in _walk_skills(skills_dir):
            installed_names.add(entry["name"])

    categories = {}

    for source, container_path in [
        ("builtin", "/opt/hermes/skills"),
        ("optional", "/opt/hermes/optional-skills"),
    ]:
        output = await asyncio.to_thread(
            docker.exec_in_container,
            instance.container_id,
            f"find {container_path} -name 'SKILL.md' -type f 2>/dev/null",
        )
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            skill_dir = os.path.dirname(line)
            rel = os.path.relpath(skill_dir, container_path)
            cat = rel.split("/")[0] if "/" in rel else "other"

            md_content = await asyncio.to_thread(
                docker.exec_in_container,
                instance.container_id,
                f"head -c 2048 '{line}'",
            )
            meta = _parse_skill_md(md_content)

            if cat not in categories:
                categories[cat] = {"name": cat, "display_name": cat, "skills": []}

            categories[cat]["skills"].append({
                "name": rel,
                "display_name": meta.get("name") or rel.split("/")[-1],
                "description": meta.get("description", ""),
                "source": source,
                "installed": rel in installed_names,
                "tags": meta.get("tags", []),
            })

    total = sum(len(c["skills"]) for c in categories.values())
    return {
        "categories": list(categories.values()),
        "total_available": total,
    }


async def install_skill(
    db: AsyncSession,
    instance: AgentInstance,
    skill_name: str,
    source: str,
):
    """Install a skill from the container's built-in/optional library."""
    docker = DockerAdapter()
    status = docker.get_container_status(instance.container_id)
    if status != "running":
        raise BusinessError(-1, "实例必须处于运行状态才能安装技能")

    if source == "builtin":
        src_path = f"/opt/hermes/skills/{skill_name}"
    elif source == "optional":
        src_path = f"/opt/hermes/optional-skills/{skill_name}"
    else:
        raise BusinessError(-1, f"不支持的来源: {source}")

    category = skill_name.rsplit("/", 1)[0] if "/" in skill_name else ""
    if category:
        await asyncio.to_thread(
            docker.exec_in_container,
            instance.container_id,
            f"mkdir -p /opt/data/skills/{category}",
        )

    await asyncio.to_thread(
        docker.exec_in_container,
        instance.container_id,
        f"cp -r '{src_path}' '/opt/data/skills/{skill_name}'",
    )

    existing = await db.execute(
        select(InstanceSkillConfig).where(
            InstanceSkillConfig.instance_id == instance.id,
            InstanceSkillConfig.skill_name == skill_name,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(InstanceSkillConfig(
            instance_id=instance.id,
            skill_name=skill_name,
            source=source,
            enabled=True,
        ))
        await db.commit()


async def uninstall_skill(
    db: AsyncSession,
    instance: AgentInstance,
    skill_name: str,
):
    """Remove an installed skill."""
    skill_path = os.path.join(instance.data_dir, "skills", skill_name)
    disabled_path = os.path.join(instance.data_dir, "skills", ".disabled", skill_name)

    import shutil
    if os.path.isdir(skill_path):
        shutil.rmtree(skill_path)
    if os.path.isdir(disabled_path):
        shutil.rmtree(disabled_path)

    result = await db.execute(
        select(InstanceSkillConfig).where(
            InstanceSkillConfig.instance_id == instance.id,
            InstanceSkillConfig.skill_name == skill_name,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg:
        await db.delete(cfg)
        await db.commit()


async def toggle_skill(
    db: AsyncSession,
    instance: AgentInstance,
    skill_name: str,
    enabled: bool,
):
    """Enable or disable a skill by moving to/from .disabled directory."""
    skills_dir = os.path.join(instance.data_dir, "skills")
    disabled_dir = os.path.join(skills_dir, ".disabled")
    os.makedirs(disabled_dir, exist_ok=True)

    import shutil
    active_path = os.path.join(skills_dir, skill_name)
    disabled_path = os.path.join(disabled_dir, skill_name)

    if not enabled and os.path.isdir(active_path):
        dest_parent = os.path.dirname(disabled_path)
        os.makedirs(dest_parent, exist_ok=True)
        shutil.move(active_path, disabled_path)
    elif enabled and os.path.isdir(disabled_path):
        dest_parent = os.path.dirname(active_path)
        os.makedirs(dest_parent, exist_ok=True)
        shutil.move(disabled_path, active_path)

    result = await db.execute(
        select(InstanceSkillConfig).where(
            InstanceSkillConfig.instance_id == instance.id,
            InstanceSkillConfig.skill_name == skill_name,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg:
        cfg.enabled = enabled
    else:
        db.add(InstanceSkillConfig(
            instance_id=instance.id,
            skill_name=skill_name,
            source="custom",
            enabled=enabled,
        ))
    await db.commit()


async def create_custom_skill(
    db: AsyncSession,
    instance: AgentInstance,
    name: str,
    display_name: str,
    description: str,
    tags: list[str],
    content: str,
):
    """Create a user-defined custom skill."""
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise BusinessError(-1, "技能名称只允许字母、数字、下划线和连字符")

    skill_dir = os.path.join(instance.data_dir, "skills", name)
    if os.path.isdir(skill_dir):
        raise BusinessError(-1, f"技能 {name} 已存在")

    os.makedirs(skill_dir, exist_ok=True)

    tags_str = ", ".join(f'"{t}"' for t in tags) if tags else ""
    frontmatter = (
        f"---\n"
        f"name: {display_name}\n"
        f"description: \"{description}\"\n"
        f"version: 1.0.0\n"
        f"author: User\n"
        f"metadata:\n"
        f"  hermes:\n"
        f"    tags: [{tags_str}]\n"
        f"---\n\n"
    )

    with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
        f.write(frontmatter + content)

    db.add(InstanceSkillConfig(
        instance_id=instance.id,
        skill_name=name,
        source="custom",
        enabled=True,
        custom_content=content,
    ))
    await db.commit()


async def update_custom_skill(
    db: AsyncSession,
    instance: AgentInstance,
    skill_name: str,
    display_name: str | None,
    description: str | None,
    tags: list[str] | None,
    content: str | None,
):
    """Update an existing custom skill."""
    result = await db.execute(
        select(InstanceSkillConfig).where(
            InstanceSkillConfig.instance_id == instance.id,
            InstanceSkillConfig.skill_name == skill_name,
            InstanceSkillConfig.source == "custom",
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise BusinessError(-1, f"自定义技能 {skill_name} 不存在")

    skill_dir = os.path.join(instance.data_dir, "skills", skill_name)
    skill_path = os.path.join(skill_dir, "SKILL.md")

    if not os.path.isfile(skill_path):
        raise BusinessError(-1, f"技能文件不存在")

    if content is not None:
        cfg.custom_content = content
        _display = display_name or skill_name
        _desc = description or ""
        _tags = tags or []
        tags_str = ", ".join(f'"{t}"' for t in _tags) if _tags else ""
        frontmatter = (
            f"---\n"
            f"name: {_display}\n"
            f"description: \"{_desc}\"\n"
            f"version: 1.0.0\n"
            f"author: User\n"
            f"metadata:\n"
            f"  hermes:\n"
            f"    tags: [{tags_str}]\n"
            f"---\n\n"
        )
        with open(skill_path, "w") as f:
            f.write(frontmatter + content)

    await db.commit()


async def delete_custom_skill(
    db: AsyncSession,
    instance: AgentInstance,
    skill_name: str,
):
    """Delete a custom skill."""
    result = await db.execute(
        select(InstanceSkillConfig).where(
            InstanceSkillConfig.instance_id == instance.id,
            InstanceSkillConfig.skill_name == skill_name,
            InstanceSkillConfig.source == "custom",
        )
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise BusinessError(-1, f"自定义技能 {skill_name} 不存在")

    import shutil
    skill_dir = os.path.join(instance.data_dir, "skills", skill_name)
    if os.path.isdir(skill_dir):
        shutil.rmtree(skill_dir)

    await db.delete(cfg)
    await db.commit()
