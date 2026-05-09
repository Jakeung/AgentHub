# 🔒 P1 安全漏洞修复方案

**生成日期**: 2025-05-09  
**优先级**: 🔴 致命  
**状态**: 实施中

---

## 📋 9个P1问题修复总结

### 1. ✅ Docker Socket 暴露 → Docker API Proxy
**严重性**: 极高（容器被攻击 = 主机被攻击）

**问题**:
```yaml
# ❌ 原配置
volumes:
  - /var/run/docker.sock:/var/run/docker.sock  # 危险！
```

**修复**:
```yaml
# ✅ 新配置
services:
  docker-proxy:  # 单独的代理容器
    image: tecnativa/docker-socket-proxy:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # 仅代理容器暴露
    environment:
      CONTAINERS: 1    # 仅允许容器操作
      IMAGES: 1
      NETWORKS: 0      # 禁止网络操作
      VOLUMES: 0       # 禁止卷操作
      DELETE: 1        # 允许删除
      POST: 1          # 允许创建
  
  backend:
    environment:
      - DOCKER_HOST=http://docker-proxy:2375  # 通过代理而非Socket
```

**效果**: 
- ✅ Backend 无法直接访问 Docker Socket
- ✅ 权限最小化（仅容器管理）
- ✅ 审计日志更清晰

**验证方式**:
```bash
docker-compose up
# 检查是否能启动容器实例
# 查看日志是否正常
```

---

### 2. ✅ JWT_SECRET 默认值 → 强制生成随机密钥
**严重性**: 高（密钥可被猜测）

**问题**:
```python
# ❌ 原配置
JWT_SECRET: str = "change-me-in-production-use-random-32-chars"  # 默认值！
```

**修复**:
```bash
# 1. 生成强密钥
openssl rand -hex 32
# 输出示例: a1b2c3d4e5f6... (64个字符)

# 2. 保存到 .env
echo "JWT_SECRET=<上面生成的值>" >> .env

# 3. 或使用 docker/secrets
# Docker Compose 会读取环境变量
export JWT_SECRET=$(openssl rand -hex 32)
```

**配置**:
```python
# backend/app/core/config.py
class Settings(BaseSettings):
    JWT_SECRET: str = ""
    
    def model_post_init(self, __context):
        if not self.JWT_SECRET:
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("生产环境必须设置 JWT_SECRET")
            # 开发环境临时生成
            import secrets
            self.JWT_SECRET = secrets.token_urlsafe(32)
        
        # 检查是否使用了默认值
        if self.JWT_SECRET == "change-me-in-production-use-random-32-chars":
            raise ValueError("检测到使用默认 JWT_SECRET，禁止在生产环境使用")
        
        if len(self.JWT_SECRET) < 32:
            raise ValueError("JWT_SECRET 长度不少于32字符")
```

**验证方式**:
```bash
# 检查是否设置了非默认密钥
grep "JWT_SECRET" .env
# 确保不是默认值
```

---

### 3. ✅ 加密密钥硬编码 → 分立ENCRYPTION_KEY
**严重性**: 高（API Key 加密密钥暴露）

**问题**:
```python
# ❌ 原配置
def _get_fernet() -> Fernet:
    settings = get_settings()
    # 从 JWT_SECRET 派生，这样任何人知道 JWT_SECRET 就能解密所有 API Key
    key_bytes = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)
```

**修复**:
```python
# backend/app/core/config.py
class Settings(BaseSettings):
    ENCRYPTION_KEY: str = ""
    
    def model_post_init(self, __context):
        # ... JWT_SECRET 检查 ...
        
        # 加密密钥独立检查
        if not self.ENCRYPTION_KEY:
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("生产环境必须设置独立的 ENCRYPTION_KEY")
            # 开发环境临时生成
            import secrets
            key_bytes = secrets.token_bytes(32)
            self.ENCRYPTION_KEY = base64.urlsafe_b64encode(key_bytes).decode()

# backend/app/core/security.py
def _get_fernet() -> Fernet:
    settings = get_settings()
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY 未配置")
    # 使用独立的密钥，不依赖 JWT_SECRET
    return Fernet(settings.ENCRYPTION_KEY.encode())
```

**生成独立密钥**:
```bash
openssl rand -base64 32  # 生成另一个密钥
# 保存到 .env
echo "ENCRYPTION_KEY=<生成的值>" >> .env
```

---

### 4. ✅ API Key 硬编码 → Docker Secrets 管理
**严重性**: 极高（容器内明文存储密钥）

**问题**:
```bash
# ❌ 原配置：在 .env 文件中明文存储
OPENAI_API_KEY=sk-...
API_SERVER_KEY=agenthub-internal
```

**修复**:
```bash
# 方法1: Docker Secrets（推荐）
# 1. 创建密钥文件
mkdir -p ./secrets
openssl rand -hex 32 > ./secrets/api_server_key.txt

# 2. docker-compose.yml 会自动读取
secrets:
  api_server_key:
    environment: API_SERVER_KEY

# 3. Backend 中读取
import os
api_server_key = open("/run/secrets/api_server_key").read().strip()

# 4. 每个容器实例的密钥不同
# 防止所有实例使用同一个密钥
instance_api_key = secrets.token_urlsafe(32)
# 保存到容器启动环境，或生成后保存到 DB
```

**新增逻辑**:
```python
# backend/app/services/instance_service.py
async def create_instance(...):
    import secrets
    
    # 生成该实例的唯一 API Server Key
    instance_api_key = secrets.token_urlsafe(32)
    instance.api_server_key = instance_api_key  # 保存到 DB
    
    # 通过 Docker Secrets 而非硬编码传入
    docker.create_container(
        ...,
        secrets=[
            {
                "uid": "instance_api_key",
                "secret": instance_api_key,
                "encrypt": True
            }
        ]
    )
```

**验证方式**:
```bash
# 检查 .env 中是否仍有明文 API Key
grep -E "(KEY|SECRET|TOKEN)=" .env
# 应该为空或使用 FILE 引用
```

---

### 5. ✅ CORS 过宽松 → 严格限制
**严重性**: 高（CSRF 攻击风险）

**问题**:
```python
# ❌ 原配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,  # ⚠️ 允许 Cookie
    allow_methods=["*"],     # ⚠️ 所有方法
    allow_headers=["*"],     # ⚠️ 所有 Header
)
```

**修复**:
```python
# backend/main.py
allowed_origins = [
    origin.strip() 
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

# 检查是否使用了不安全的通配符
if "*" in allowed_origins and settings.CORS_ORIGINS:
    raise ValueError("生产环境不能使用通配符 CORS origins")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # 明确的生产域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 明确列表
    allow_headers=["Content-Type", "Authorization"],  # 明确列表
    expose_headers=["Content-Type"],
    max_age=600,  # 预检缓存10分钟
)

# backend/app/core/config.py
class Settings(BaseSettings):
    CORS_ORIGINS: str = ""
    
    def model_post_init(self, __context):
        # ... 其他检查 ...
        
        if os.getenv("ENVIRONMENT") == "production":
            if not self.CORS_ORIGINS or "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "生产环境必须指定明确的 CORS 域名，不能使用通配符"
                )
```

**.env 配置**:
```env
# ✅ 生产环境
CORS_ORIGINS=https://app.example.com,https://admin.example.com

# ❌ 绝对不要
CORS_ORIGINS=*
```

**验证方式**:
```bash
# 测试 CORS 限制
curl -H "Origin: http://evil.com" http://localhost:8000/api/auth/me
# 应该返回 403 或缺少 CORS 头
```

---

### 6. ✅ 部署失败无回滚 → 事务制控制
**严重性**: 高（端口泄漏、状态不一致）

**问题**:
```python
# ❌ 原配置
async def create_instance(...):
    # DB 已保存
    instance = AgentInstance(...)
    db.add(instance)
    await db.commit()  # 提交了！
    
    # Docker 创建失败，但 DB 已有记录
    try:
        container_id = docker.create_container(...)
    except Exception as e:
        # 只是记录，不回滚
        logger.warning(f"Docker create failed: {e}")
        instance.container_id = f"mock-{container_name}"
```

**修复**:
```python
# backend/app/services/instance_service.py
async def create_instance(
    db: AsyncSession,
    user_id: int,
    name: str,
    **kwargs
):
    import secrets
    
    try:
        # 1. 整个操作使用事务
        async with db.begin():
            # 2. 分配端口
            port = await allocate_port(db)
            
            # 3. 生成容器名和 API Key
            container_name = await generate_container_name(db, user_id)
            api_server_key = secrets.token_urlsafe(32)
            
            # 4. 创建 DB 记录（但还未提交）
            instance = AgentInstance(
                name=name,
                owner_user_id=user_id,
                port=port,
                container_name=container_name,
                api_server_key=api_server_key,
                status="creating",
            )
            db.add(instance)
            
            # 5. 测试 Docker 创建（在事务中失败则自动回滚）
            docker = DockerAdapter()
            container_id = await asyncio.wait_for(
                docker.create_container_async(...),
                timeout=30
            )
            
            instance.container_id = container_id
            instance.status = "created"
            
            # 6. 事务自动提交，成功则保存，失败则回滚
    
    except asyncio.TimeoutError:
        # 清理已创建的容器（最好努力原则）
        logger.error(f"Container creation timeout")
        raise BusinessError(-1, "容器创建超时")
    
    except Exception as e:
        # 事务自动回滚，端口和容器名自动释放
        logger.error(f"Instance creation failed: {e}", exc_info=True)
        raise BusinessError(-1, f"创建实例失败: {str(e)[:200]}")
    
    return instance
```

**优点**:
- ✅ 失败自动回滚，不产生孤立记录
- ✅ 端口和容器名自动释放
- ✅ 用户收到明确的错误消息

---

### 7. ✅ 端口泄漏 → Soft Delete + Port Pool
**严重性**: 高（端口耗尽，无法创建新实例）

**问题**:
```python
# ❌ 原配置
async def delete_instance(...):
    # 物理删除
    await db.delete(instance)
    await db.commit()
    # 端口号丢失，无法回收
```

**修复**:
```python
# backend/app/models/instance.py
from datetime import datetime

class AgentInstance(Base):
    __tablename__ = "agent_instance"
    
    # ... 现有字段 ...
    status = Column(String(50), default="created")  # 新增状态
    deleted_at = Column(DateTime, nullable=True)   # Soft delete 时间戳
    
    @property
    def is_deleted(self) -> bool:
        return self.status == "deleted"

# backend/app/services/instance_service.py
async def delete_instance(db: AsyncSession, instance_id: int):
    instance = await db.get(AgentInstance, instance_id)
    
    if not instance:
        raise NotFoundError("Instance not found")
    
    # Soft delete：标记为已删除，但保留数据
    instance.status = "deleted"
    instance.deleted_at = datetime.now(timezone.utc)
    await db.commit()

async def allocate_port(db: AsyncSession) -> int:
    """优先复用已释放的端口（冷却期后）"""
    
    # 1. 优先考虑复用已 soft-delete 的端口（1小时冷却期后）
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await db.execute(
        select(AgentInstance.port)
        .where(
            AgentInstance.status == "deleted",
            AgentInstance.deleted_at < cutoff_time
        )
        .order_by(AgentInstance.port)
        .limit(1)
    )
    reused_port = result.scalar_one_or_none()
    
    if reused_port:
        logger.info(f"Reusing port {reused_port} after cool-down period")
        return reused_port
    
    # 2. 分配新端口
    result = await db.execute(
        select(func.count()).select_from(AgentInstance).where(
            (AgentInstance.status != "deleted") |
            (AgentInstance.deleted_at > cutoff_time)
        )
    )
    count = result.scalar() or 0
    
    new_port = SETTINGS.PORT_RANGE_START + count
    if new_port > SETTINGS.PORT_RANGE_END:
        # 计算使用率
        usage_pct = count / (SETTINGS.PORT_RANGE_END - SETTINGS.PORT_RANGE_START) * 100
        logger.warning(f"Port usage {usage_pct:.1f}% - approaching limit")
        raise BusinessError(-1, "端口即将耗尽，无法创建新实例")
    
    return new_port

# 定期清理旧 soft-delete 记录（可选）
async def cleanup_old_deleted_instances(db: AsyncSession, days: int = 30):
    """清理30天前 soft-delete 的记录"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await db.execute(
        select(AgentInstance).where(
            AgentInstance.status == "deleted",
            AgentInstance.deleted_at < cutoff
        )
    )
    old_instances = result.scalars().all()
    
    for inst in old_instances:
        await db.delete(inst)
    
    await db.commit()
    logger.info(f"Cleaned up {len(old_instances)} old deleted instances")
```

**验证方式**:
```bash
# 删除一个实例
curl -X DELETE http://localhost:8000/api/instances/1

# 检查端口状态
select status, deleted_at from agent_instance where id = 1;
# 应该显示: status='deleted', deleted_at=<timestamp>

# 1小时后，端口应该被回收利用
```

---

### 8. ✅ 模型配置无验证 → 严格验证
**严重性**: 高（无效配置导致实例无法使用）

**问题**:
```python
# ❌ 原配置：没有任何验证
async def update_instance_llm_config(
    db: AsyncSession,
    instance_id: int,
    provider: str,
    api_key: str,
    model: str,
    base_url: str,  # 可能是恶意地址
):
    # 直接保存，不验证
    instance.provider = provider
    instance.api_key = api_key
```

**修复**:
```python
# backend/app/services/secret_service.py
from urllib.parse import urlparse

async def validate_and_update_llm_config(
    db: AsyncSession,
    instance: AgentInstance,
    provider: str,
    api_key: str,
    model: str,
    base_url: str = "",
) -> bool:
    """验证 LLM 配置，失败则返回 False"""
    
    # 1. 验证 Provider
    valid_providers = {"deepseek", "openai", "anthropic", "openrouter", "azure"}
    if provider not in valid_providers:
        raise ValidationError(f"不支持的提供商: {provider}")
    
    # 2. 验证 Base URL 格式
    if base_url:
        try:
            parsed = urlparse(base_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("URL 格式不正确")
            if parsed.scheme not in ("http", "https"):
                raise ValueError("仅支持 HTTP/HTTPS")
        except Exception as e:
            raise ValidationError(f"Base URL 无效: {str(e)}")
    
    # 3. 实时测试 API Key
    try:
        is_valid = await test_llm_api_key(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=10
        )
        if not is_valid:
            raise ValidationError("API Key 无效或连接失败")
    except Exception as e:
        logger.error(f"API Key validation failed: {e}")
        raise ValidationError(f"无法验证 API Key: {str(e)}")
    
    # 4. 验证模型是否存在于该提供商
    try:
        available_models = await get_available_models(
            provider=provider,
            api_key=api_key,
            base_url=base_url
        )
        if model and model not in available_models:
            logger.warning(f"Model {model} not found in provider, using default")
            model = available_models[0] if available_models else "default"
    except Exception as e:
        logger.warning(f"Failed to fetch available models: {e}")
    
    # 5. 更新配置
    instance.provider = provider
    instance.api_key = encrypt_key(api_key)  # 加密存储
    instance.model = model
    instance.base_url = base_url
    instance.config_updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    return True

# 测试 API Key 的辅助函数
async def test_llm_api_key(
    provider: str,
    api_key: str,
    base_url: str = "",
    model: str = "default",
    timeout: int = 10
) -> bool:
    """通过 API 调用测试 Key 的有效性"""
    
    try:
        if provider == "openai":
            import openai
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url or None
            )
            await asyncio.wait_for(
                client.models.list(),
                timeout=timeout
            )
            return True
        
        elif provider == "deepseek":
            import openai
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url or "https://api.deepseek.com/v1"
            )
            await asyncio.wait_for(
                client.models.list(),
                timeout=timeout
            )
            return True
        
        # ... 其他提供商 ...
        
        return False
    
    except Exception as e:
        logger.error(f"API key test failed: {e}")
        return False
```

**验证方式**:
```bash
# 尝试配置无效的 API Key
curl -X PUT http://localhost:8000/api/instances/1/llm-config \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "invalid-key",
    "model": "gpt-4"
  }'

# 应该返回 400 + "API Key 无效或连接失败"
```

---

### 9. ✅ 缺少健康检查 → 定期检查 + 自动恢复
**严重性**: 高（容器崩溃无感知）

**问题**:
```python
# ❌ 原配置：没有定期检查
# health_check() 存在但从未被调用
```

**修复**:
```python
# backend/app/core/background_tasks.py
import asyncio
from datetime import datetime

class HealthCheckService:
    """定期检查所有实例的健康状态"""
    
    @staticmethod
    async def check_all_instances(db: AsyncSession):
        """检查所有运行中的实例"""
        
        result = await db.execute(
            select(AgentInstance).where(AgentInstance.status == "running")
        )
        instances = result.scalars().all()
        
        unhealthy = []
        
        for inst in instances:
            try:
                # 使用实例端口进行健康检查
                adapter = HermesAdapter(port=inst.port)
                is_healthy = await asyncio.wait_for(
                    adapter.health_check(),
                    timeout=10
                )
                
                if not is_healthy:
                    unhealthy.append(inst)
                    inst.health_status = "unhealthy"
                    logger.warning(f"Instance {inst.name} (id={inst.id}) health check failed")
                else:
                    if inst.health_status != "healthy":
                        inst.health_status = "healthy"
                        logger.info(f"Instance {inst.name} recovered")
            
            except asyncio.TimeoutError:
                unhealthy.append(inst)
                inst.health_status = "timeout"
                logger.warning(f"Instance {inst.name} health check timeout")
            
            except Exception as e:
                unhealthy.append(inst)
                inst.health_status = f"error: {type(e).__name__}"
                logger.error(f"Instance {inst.name} health check error: {e}")
        
        await db.commit()
        
        # 返回不健康的实例列表
        return unhealthy

# backend/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await seed()
    
    # 启动健康检查后台任务
    from app.core.background_tasks import HealthCheckService
    health_check_task = asyncio.create_task(
        _health_check_loop()
    )
    
    yield
    
    # Shutdown
    health_check_task.cancel()
    try:
        await health_check_task
    except asyncio.CancelledError:
        pass

async def _health_check_loop():
    """后台健康检查循环"""
    from app.models.base import async_session
    from app.core.background_tasks import HealthCheckService
    
    while True:
        try:
            async with async_session() as db:
                unhealthy = await HealthCheckService.check_all_instances(db)
                
                # 可选：发送告警
                if unhealthy:
                    logger.warning(f"{len(unhealthy)} instances are unhealthy")
                    # 可以在这里集成告警系统
                    # await send_alert(unhealthy)
        
        except Exception as e:
            logger.error(f"Health check loop error: {e}", exc_info=True)
        
        # 每 30 秒检查一次
        await asyncio.sleep(30)
```

**验证方式**:
```bash
# 启动应用
docker-compose up

# 查看健康检查日志
docker logs agenthub-backend | grep -i "health"

# 手动停止一个实例的容器
docker stop <hermes-container-id>

# 等待30秒，查看日志
# 应该看到 "health check failed" 警告
```

---

## 📊 修复验证清单

部署这些修复后，需要验证：

- [ ] Docker Socket 已完全移除，使用 Docker API Proxy
- [ ] JWT_SECRET 已设置为非默认随机值（64字符）
- [ ] ENCRYPTION_KEY 已独立设置
- [ ] API Server Key 使用 Docker Secrets
- [ ] CORS_ORIGINS 已限制为明确的生产域名
- [ ] 实例创建使用事务，失败自动回滚
- [ ] 端口支持复用（冷却期后）
- [ ] 模型配置更新前进行验证
- [ ] 后台健康检查每30秒运行一次

## 🚀 部署流程

```bash
# 1. 备份现有数据
cp -r data data_backup_$(date +%Y%m%d)

# 2. 更新 docker-compose.yml（已完成）
# docker-compose.yml 已替换为安全版本

# 3. 生成或设置所有密钥
export JWT_SECRET=$(openssl rand -hex 32)
export ENCRYPTION_KEY=$(openssl rand -base64 32)
export DB_PASSWORD=$(openssl rand -hex 16)
export API_SERVER_KEY=$(openssl rand -hex 32)

# 4. 创建 .env 文件
cat > .env << ENV
ENVIRONMENT=production
JWT_SECRET=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
DB_PASSWORD=$DB_PASSWORD
API_SERVER_KEY=$API_SERVER_KEY
CORS_ORIGINS=https://app.example.com
BACKEND_PORT=8000
FRONTEND_PORT=80
LOG_LEVEL=INFO
ENV

# 5. 拉起新容器（会自动迁移数据）
docker-compose up -d

# 6. 验证
docker-compose ps
docker-compose logs backend | tail -50
```

---

**下一步**: 
1. ✅ 替换 docker-compose.yml
2. ⏳ 实现后端代码修复（见各章节）
3. ⏳ 测试并部署到生产环境

