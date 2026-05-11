"""Instance service - state machine, port allocation, Docker orchestration."""
import asyncio
import json
import os
import secrets
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlparse

from app.core.config import get_settings
from app.core.exceptions import BusinessError, ValidationError
from app.models.instance import AgentInstance
from app.adapters.docker_adapter import DockerAdapter

logger = logging.getLogger(__name__)
settings = get_settings()

VALID_TRANSITIONS = {
    "start": {"stopped", "error"},
    "stop": {"running"},
    "restart": {"running"},
    "delete": {"stopped", "error"},
    "upgrade": {"stopped", "running", "error"},
}

HERMES_IMAGE = "nousresearch/hermes-agent:latest"
IMAGES_DIR = "/app/images" if os.path.isdir("/app/images") else "./images"


async def load_local_images():
    """Load .tar image files from the images directory into Docker."""
    if not os.path.isdir(IMAGES_DIR):
        return
    docker = DockerAdapter()
    for fname in os.listdir(IMAGES_DIR):
        if fname.endswith(".tar"):
            tar_path = os.path.join(IMAGES_DIR, fname)
            try:
                await asyncio.to_thread(docker.load_image_from_tar, tar_path)
                logger.info(f"Loaded image from {fname}")
            except Exception as e:
                logger.warning(f"Failed to load image {fname}: {e}")


def check_upgrade_available(instance: AgentInstance) -> dict:
    """Check if a newer image version is available for the instance."""
    docker = DockerAdapter()
    latest_id = docker.get_image_id(HERMES_IMAGE)
    container_image_id = None
    if instance.container_id and not instance.container_id.startswith("mock-"):
        container_image_id = docker.get_container_image_id(instance.container_id)

    available = (
        latest_id is not None
        and container_image_id is not None
        and latest_id != container_image_id
    )
    return {
        "available": available,
        "current_image_id": (container_image_id or "")[:19],
        "latest_image_id": (latest_id or "")[:19],
    }


async def _build_llm_env(db: AsyncSession) -> dict:
    """Build LLM environment variables from system settings."""
    from app.models.system_setting import SystemSetting
    sys_settings = {}
    try:
        result = await db.execute(select(SystemSetting))
        for s in result.scalars().all():
            sys_settings[s.key] = s.value
    except Exception:
        pass

    llm_env = {}
    api_key = sys_settings.get("hermes_llm_api_key", "")
    provider = sys_settings.get("hermes_llm_provider", "")
    model_name = sys_settings.get("hermes_llm_model", "")
    base_url = sys_settings.get("hermes_llm_base_url", "")
    if api_key:
        if provider == "openrouter":
            llm_env["OPENROUTER_API_KEY"] = api_key
        else:
            llm_env["OPENAI_API_KEY"] = api_key
    if base_url:
        llm_env["OPENAI_BASE_URL"] = base_url
    if model_name:
        llm_env["HERMES_DEFAULT_MODEL"] = model_name
    return llm_env


async def allocate_port(db: AsyncSession) -> int:
    """Find first available port not used in DB or by Docker containers."""
    result = await db.execute(
        select(AgentInstance.port).where(AgentInstance.status != "deleted")
    )
    db_ports = {row[0] for row in result.all()}

    try:
        docker = DockerAdapter()
        docker_ports = docker.get_used_host_ports()
    except Exception:
        docker_ports = set()

    occupied = db_ports | docker_ports

    for port in range(settings.PORT_RANGE_START, settings.PORT_RANGE_END + 1):
        if port not in occupied:
            return port

    raise BusinessError(-11, "端口已耗尽，无法创建新实例")


async def generate_container_name(db: AsyncSession, username: str) -> str:
    """Generate a unique container name, checking both DB and Docker."""
    result = await db.execute(
        select(func.count()).select_from(AgentInstance)
        .where(AgentInstance.container_name.like(f"hermes-{username}-%"))
    )
    count = result.scalar() or 0

    docker = DockerAdapter()
    name = f"hermes-{username}-{count + 1:03d}"
    while docker.container_exists(name):
        count += 1
        name = f"hermes-{username}-{count + 1:03d}"
    return name


async def create_instance(
    db: AsyncSession,
    user_id: int,
    username: str,
    name: str,
    cpu_limit: float = 1.0,
    memory_limit_mb: int = 2048,
    env_config: dict | None = None,
) -> AgentInstance:
    """Create a new Hermes instance with transaction support."""
    try:
        async with db.begin():
            # 1. Check if user already has an instance
            existing = await db.execute(
                select(AgentInstance).where(
                    AgentInstance.owner_user_id == user_id,
                    AgentInstance.status != "deleted",
                )
            )
            if existing.scalars().first():
                raise ValidationError("每个用户只能创建一个实例")

            # 2. Allocate port and generate container name (within transaction)
            port = await allocate_port(db)
            container_name = await generate_container_name(db, username)
            api_server_key = secrets.token_urlsafe(32)

            # 3. Create data directory (container-internal path for file I/O)
            data_dir = os.path.abspath(
                os.path.join(settings.HERMES_DATA_ROOT, container_name)
            )
            try:
                os.makedirs(data_dir, exist_ok=True)
            except OSError as e:
                logger.warning(f"Cannot create data dir {data_dir}: {e}")
                data_dir = os.path.abspath(os.path.join("./data/hermes", container_name))
                os.makedirs(data_dir, exist_ok=True)

            # Host-side path for Docker volume mounts
            if settings.HOST_DATA_ROOT:
                host_data_dir = os.path.join(settings.HOST_DATA_ROOT, container_name)
            else:
                host_data_dir = data_dir

            # 4. Build LLM environment variables from system settings
            llm_env = await _build_llm_env(db)

            # 5. Create DB record (within transaction)
            instance = AgentInstance(
                name=name,
                container_name=container_name,
                port=port,
                status="creating",
                cpu_limit=cpu_limit,
                memory_limit_mb=memory_limit_mb,
                data_dir=data_dir,
                api_server_key=api_server_key,
                env_config=json.dumps(env_config or {}, ensure_ascii=False),
                owner_user_id=user_id,
            )
            db.add(instance)

            # 6. Try to create Docker container with timeout
            try:
                docker = DockerAdapter()
                container_id = await asyncio.wait_for(
                    asyncio.to_thread(
                        docker.create_container,
                        HERMES_IMAGE,
                        container_name,
                        port,
                        host_data_dir,
                        memory_limit_mb,
                        cpu_limit,
                        env_config or {},
                        api_server_key,
                        llm_env,
                    ),
                    timeout=30,
                )
                instance.container_id = container_id
                instance.status = "stopped"
            except asyncio.TimeoutError:
                logger.error(f"Container creation timeout for {container_name}")
                raise BusinessError(-1, "容器创建超时")
            except Exception as e:
                logger.warning(f"Docker create failed (dev mode?): {e}")
                instance.container_id = f"mock-{container_name}"
                instance.status = "stopped"
                instance.health_status = "docker_unavailable"

            # Transaction auto-commits on success, auto-rolls back on exception
            return instance

    except (ValidationError, BusinessError):
        raise
    except Exception as e:
        logger.error(f"Instance creation failed: {e}", exc_info=True)
        raise BusinessError(-1, f"创建实例失败: {str(e)[:200]}")


async def _write_hermes_config(instance: AgentInstance):
    """Write config.yaml into the Hermes data dir before container starts."""
    from app.models.base import async_session as _async_session
    from app.models.system_setting import SystemSetting

    sys_settings = {}
    try:
        async with _async_session() as db:
            result = await db.execute(select(SystemSetting))
            for s in result.scalars().all():
                sys_settings[s.key] = s.value
    except Exception:
        pass

    model_name = sys_settings.get("hermes_llm_model", "deepseek-chat")
    provider = sys_settings.get("hermes_llm_provider", "custom")
    base_url = sys_settings.get("hermes_llm_base_url", "")

    config_content = f'model:\n  default: "{model_name}"\n  provider: "{provider}"\n'
    if base_url:
        config_content += f'  base_url: "{base_url}"\n'

    try:
        config_path = os.path.join(instance.data_dir, "config.yaml")
        with open(config_path, "w") as f:
            f.write(config_content)
        logger.info(f"Wrote config.yaml for {instance.container_name}")
    except Exception as e:
        logger.warning(f"Failed to write config.yaml for {instance.container_name}: {e}")


async def start_instance(db: AsyncSession, instance: AgentInstance):
    _check_transition(instance, "start")
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            docker = DockerAdapter()
            if instance.container_id and instance.container_id.startswith("mock-"):
                logger.info(f"Re-creating container for mock instance {instance.container_name}")
                abs_data_dir = os.path.abspath(instance.data_dir)
                os.makedirs(abs_data_dir, exist_ok=True)
                if settings.HOST_DATA_ROOT:
                    host_data_dir = os.path.join(settings.HOST_DATA_ROOT, instance.container_name)
                else:
                    host_data_dir = abs_data_dir

                try:
                    env = json.loads(instance.env_config) if instance.env_config else {}
                except (json.JSONDecodeError, TypeError):
                    env = {}

                llm_env = await _build_llm_env(db)

                container_id = docker.create_container(
                    image=HERMES_IMAGE,
                    name=instance.container_name,
                    port=instance.port,
                    data_dir=host_data_dir,
                    mem_limit_mb=instance.memory_limit_mb,
                    cpu_limit=instance.cpu_limit,
                    environment=env,
                    api_server_key=instance.api_server_key or "",
                    llm_env=llm_env,
                )
                instance.container_id = container_id

            await asyncio.wait_for(
                asyncio.to_thread(docker.start_container, instance.container_id),
                timeout=30,
            )
            instance.status = "running"
            instance.health_status = "healthy"

            # Write config.yaml (synchronous, before hermes fully initializes)
            await _write_hermes_config(instance)

            break

        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            instance.status = "error"
            instance.health_status = "启动超时（30秒）"

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Start attempt {attempt+1} failed: {e}")
                await asyncio.sleep(retry_delay)
                continue
            instance.status = "error"
            instance.health_status = f"启动失败: {str(e)[:200]}"

    await db.commit()


async def stop_instance(db: AsyncSession, instance: AgentInstance):
    _check_transition(instance, "stop")
    try:
        docker = DockerAdapter()
        docker.stop_container(instance.container_id)
        instance.status = "stopped"
        instance.health_status = "unknown"
    except Exception as e:
        instance.status = "error"
        instance.health_status = f"停止失败: {str(e)[:200]}"
    await db.commit()


async def restart_instance(db: AsyncSession, instance: AgentInstance):
    _check_transition(instance, "restart")
    try:
        docker = DockerAdapter()
        docker.restart_container(instance.container_id)
        instance.status = "running"
        instance.health_status = "healthy"
    except Exception as e:
        instance.status = "error"
        instance.health_status = f"重启失败: {str(e)[:200]}"
    await db.commit()


async def validate_llm_config(
    provider: str,
    api_key: str,
    model: str,
    base_url: str = "",
) -> bool:
    """Validate LLM configuration."""
    valid_providers = {"deepseek", "openai", "anthropic", "openrouter", "azure"}

    # 1. Validate provider
    if provider not in valid_providers:
        raise ValidationError(f"不支持的提供商: {provider}")

    # 2. Validate base_url format if provided
    if base_url:
        try:
            parsed = urlparse(base_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("URL 格式不正确")
            if parsed.scheme not in ("http", "https"):
                raise ValueError("仅支持 HTTP/HTTPS")
        except Exception as e:
            raise ValidationError(f"Base URL 无效: {str(e)}")

    # 3. Test API key (basic validation)
    if not api_key or len(api_key) < 10:
        raise ValidationError("API Key 格式不正确")

    return True


async def update_instance_llm_config(
    db: AsyncSession,
    instance: AgentInstance,
    provider: str,
    api_key: str,
    model: str = "",
    base_url: str = "",
):
    """Update the instance's .env and config.yaml via shared volume."""
    await validate_llm_config(provider, api_key, model, base_url)

    data_dir = instance.data_dir

    env_lines = [
        "API_SERVER_ENABLED=true",
        "API_SERVER_HOST=0.0.0.0",
        "API_SERVER_PORT=8642",
        f"API_SERVER_KEY={instance.api_server_key}",
        "GATEWAY_ALLOW_ALL_USERS=true",
    ]

    provider_env_keys = {
        "openrouter": "OPENROUTER_API_KEY",
        "deepseek": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "azure": "OPENAI_API_KEY",
    }
    env_key = provider_env_keys.get(provider, "OPENAI_API_KEY")
    env_lines.append(f"{env_key}={api_key}")
    env_content = "\n".join(env_lines) + "\n"

    config_lines = [
        "model:",
        f'  default: "{model or "deepseek-chat"}"',
        f'  provider: "{provider or "custom"}"',
    ]
    if base_url:
        config_lines.append(f'  base_url: "{base_url}"')
    config_content = "\n".join(config_lines) + "\n"

    try:
        with open(os.path.join(data_dir, ".env"), "w") as f:
            f.write(env_content)
        with open(os.path.join(data_dir, "config.yaml"), "w") as f:
            f.write(config_content)
    except Exception as e:
        logger.error(f"Failed to write config to {data_dir}: {e}")
        raise

    if instance.status == "running":
        try:
            docker = DockerAdapter()
            docker.restart_container(instance.container_id)
        except Exception as e:
            logger.warning(f"Restart after config update failed: {e}")


async def update_instance_channels(instance: AgentInstance, channel_env_vars: dict):
    """Append channel env vars to the .env file via shared volume and restart."""
    data_dir = instance.data_dir
    env_path = os.path.join(data_dir, ".env")

    try:
        with open(env_path, "r") as f:
            current_env = f.read().strip()
    except FileNotFoundError:
        current_env = ""

    existing_lines = []
    channel_keys = set(channel_env_vars.keys())
    for line in current_env.split("\n"):
        if not line.strip():
            continue
        key = line.split("=", 1)[0] if "=" in line else ""
        if key not in channel_keys:
            existing_lines.append(line)

    for k, v in channel_env_vars.items():
        if v:
            existing_lines.append(f"{k}={v}")

    env_content = "\n".join(existing_lines) + "\n"

    try:
        with open(env_path, "w") as f:
            f.write(env_content)
    except Exception as e:
        logger.error(f"Failed to write channel env to {data_dir}: {e}")
        raise

    if instance.status == "running":
        try:
            docker = DockerAdapter()
            docker.restart_container(instance.container_id)
        except Exception as e:
            logger.warning(f"Restart after channel config update failed: {e}")


async def upgrade_instance(db: AsyncSession, instance: AgentInstance):
    """Upgrade instance to latest image while preserving data."""
    _check_transition(instance, "upgrade")
    was_running = instance.status == "running"

    try:
        docker = DockerAdapter()

        if was_running:
            try:
                docker.stop_container(instance.container_id, timeout=15)
            except Exception as e:
                logger.warning(f"Stop before upgrade failed: {e}")

        try:
            docker.remove_container(instance.container_id, force=True)
        except Exception as e:
            logger.warning(f"Remove container for upgrade failed: {e}")

        await load_local_images()

        abs_data_dir = os.path.abspath(instance.data_dir)
        os.makedirs(abs_data_dir, exist_ok=True)
        if settings.HOST_DATA_ROOT:
            host_data_dir = os.path.join(settings.HOST_DATA_ROOT, instance.container_name)
        else:
            host_data_dir = abs_data_dir

        try:
            env = json.loads(instance.env_config) if instance.env_config else {}
        except (json.JSONDecodeError, TypeError):
            env = {}
        llm_env = await _build_llm_env(db)

        container_id = await asyncio.wait_for(
            asyncio.to_thread(
                docker.create_container,
                HERMES_IMAGE,
                instance.container_name,
                instance.port,
                host_data_dir,
                instance.memory_limit_mb,
                instance.cpu_limit,
                env,
                instance.api_server_key or "",
                llm_env,
            ),
            timeout=60,
        )
        instance.container_id = container_id
        instance.status = "stopped"
        instance.health_status = "upgraded"

    except asyncio.TimeoutError:
        instance.status = "error"
        instance.health_status = "升级超时"
    except Exception as e:
        logger.error(f"Upgrade failed for {instance.container_name}: {e}", exc_info=True)
        instance.status = "error"
        instance.health_status = f"升级失败: {str(e)[:200]}"

    await db.commit()
    return was_running


async def delete_instance(db: AsyncSession, instance: AgentInstance):
    """Soft delete instance with port recovery after cooldown."""
    _check_transition(instance, "delete")
    try:
        docker = DockerAdapter()
        if instance.container_id:
            docker.remove_container(instance.container_id)
    except Exception as e:
        logger.warning(f"Container remove failed (ignored): {e}")

    # Soft delete: mark as deleted with timestamp, preserve data for recovery
    instance.status = "deleted"
    instance.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info(f"Instance {instance.name} soft-deleted")


def get_instance_stats(instance: AgentInstance) -> dict | None:
    if instance.status != "running" or not instance.container_id:
        return None
    docker = DockerAdapter()
    return docker.get_container_stats(instance.container_id)


def get_instance_logs(instance: AgentInstance, tail: int = 100) -> list[str]:
    if not instance.container_id:
        return []
    docker = DockerAdapter()
    return docker.get_container_logs(instance.container_id, tail=tail)


def _check_transition(instance: AgentInstance, action: str):
    valid_states = VALID_TRANSITIONS.get(action, set())
    if instance.status not in valid_states:
        raise BusinessError(-1, f"当前状态 [{instance.status}] 不允许执行 [{action}]")
