# 🟠 P2 & P3 问题整理

**生成日期**: 2025-05-09  
**状态**: 整理完成  
**预计修复工作量**: P2约30-40小时，P3约20-30小时

---

## 📊 问题分布概览

| 优先级 | 数量 | 类别 | 修复难度 | 工作量 |
|--------|------|------|---------|--------|
| P1 | 9 | 安全 | 高 | 30-40h |
| P2 | 12 | 功能/可靠性 | 中 | 30-40h |
| P3 | 5+ | 性能/优化 | 低 | 20-30h |

---

## 🟠 P2（高优先级）问题清单

### P2-1: 容器创建竞态条件
**文件**: `backend/app/services/instance_service.py:40-48`

**问题描述**:
```python
# ❌ 问题：在并发请求中，多个用户可能同时生成相同的容器名
count = result.scalar() or 0
return f"hermes-{username}-{count + 1:03d}"
```

**危害**:
- 并发请求导致容器名冲突
- DB 唯一约束违反，返回 500 错误
- 用户体验差

**修复难度**: ⭐⭐ (中等)

**修复方案**:
```python
# 使用行级锁
async def generate_container_name(db: AsyncSession, username: str) -> str:
    async with db.begin_nested():  # 嵌套事务
        result = await db.execute(
            select(func.count()).select_from(AgentInstance)
            .where(AgentInstance.container_name.like(f"hermes-{username}-%"))
            .with_for_update()  # 行级锁
        )
        count = result.scalar() or 0
        return f"hermes-{username}-{count + 1:03d}"
```

---

### P2-2: 启动失败状态不一致
**文件**: `backend/app/services/instance_service.py:166-192`

**问题描述**:
- 启动失败后没有重试机制
- 没有启动超时控制（Docker启动可能挂起）
- 错误信息被截断，无法调试

**危害**:
- 用户无法恢复失败的实例
- 启动过程可能无限期等待
- 调试困难

**修复难度**: ⭐⭐⭐ (中高等)

**修复方案**:
```python
async def start_instance(db: AsyncSession, instance: AgentInstance):
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            docker = DockerAdapter()
            
            # 设置启动超时
            await asyncio.wait_for(
                docker.start_container(instance.container_id),
                timeout=30
            )
            
            # 健康检查
            for _ in range(10):
                adapter = HermesAdapter(instance.port)
                if await adapter.health_check():
                    instance.status = "running"
                    instance.health_status = "healthy"
                    break
                await asyncio.sleep(1)
            else:
                raise TimeoutError("Health check timeout")
            break
        
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            instance.status = "error"
            instance.health_status = "启动超时（30秒）"
        
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            
            # 创建详细的错误日志
            await log_instance_error(db, instance.id, e)
            instance.status = "error"
            instance.health_status = type(e).__name__
    
    await db.commit()
```

---

### P2-3: 模型查询 N+1 问题
**文件**: `backend/app/api/admin_instances.py:50-62`

**问题描述**:
```python
# ❌ N+1 问题（虽然已优化为N查询，但可进一步优化）
instances = [...]
owner_ids = {inst.owner_user_id for inst in instances}
# 单独查询所有 owner
if owner_ids:
    owners = await db.execute(
        select(SysUser).where(SysUser.id.in_(owner_ids))
    )
```

**危害**:
- 列表查询时额外执行一次 owner 查询
- 大列表时性能下降

**修复难度**: ⭐⭐ (简单)

**修复方案**:
```python
# 使用 JOIN 直接获取
query = (
    select(AgentInstance, SysUser)
    .join(SysUser, SysUser.id == AgentInstance.owner_user_id, isouter=True)
    .where(AgentInstance.status != "deleted")
)

result = await db.execute(query)
instances_with_owners = result.unique().all()
```

---

### P2-4: WebSocket 连接无限制
**文件**: `backend/app/api/chat.py:95-150`

**问题描述**:
```python
# ❌ 没有连接限制
@router.websocket("/ws/chat/{instance_id}")
async def ws_chat(websocket: WebSocket, instance_id: int):
    # 单个用户可打开无限个连接
    # 没有"单实例单用户一个连接"限制
```

**危害**:
- 内存溢出
- 容器资源耗尽
- DoS 攻击风险

**修复难度**: ⭐⭐⭐ (中等)

**修复方案**:
```python
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[tuple, WebSocket] = {}
    
    async def connect(self, instance_id: int, user_id: int, websocket: WebSocket):
        key = (instance_id, user_id)
        
        # 断开旧连接
        if key in self.active_connections:
            old = self.active_connections[key]
            await old.close(code=1000)
        
        await websocket.accept()
        self.active_connections[key] = websocket
    
    def disconnect(self, instance_id: int, user_id: int):
        del self.active_connections.get((instance_id, user_id))

manager = ConnectionManager()

@router.websocket("/ws/chat/{instance_id}")
async def ws_chat(websocket: WebSocket, instance_id: int):
    token = websocket.cookies.get("auth")
    user_id = decode_token(token).get("id")
    
    try:
        await manager.connect(instance_id, user_id, websocket)
        # ...
    finally:
        manager.disconnect(instance_id, user_id)
```

---

### P2-5: 前端 user/index.vue 过大
**文件**: `web/src/views/user/index.vue` (1250+ 行)

**问题描述**:
- 单个文件包含：实例管理 + 聊天 + 设置 + 模型选择
- 圈复杂度高，难以维护
- 难以单元测试

**危害**:
- 代码复用困难
- 调试和修改成本高
- 新功能迭代缓慢

**修复难度**: ⭐⭐⭐⭐ (高)

**修复方案**:
```
web/src/views/user/
├── index.vue                 (主容器, ~200行)
├── components/
│   ├── InstanceManager.vue   (实例管理)
│   ├── ChatPanel.vue         (聊天面板)
│   ├── ConversationList.vue  (对话列表)
│   ├── SettingsPanel.vue     (设置)
│   └── ModelSelector.vue     (模型选择)
└── composables/
    ├── useChat.ts            (聊天逻辑)
    ├── useInstance.ts        (实例逻辑)
    └── useWebSocket.ts       (WebSocket)
```

预计工作量: 4-6 小时

---

### P2-6: 前端错误处理簡陋
**文件**: 多个前端文件

**问题描述**:
```javascript
// ❌ 大量空 catch blocks
try {
    const res = await secretApi.availableModels()
    // ...
} catch {}  // 无声失败
```

**危害**:
- 用户无法感知错误
- 调试困难
- 业务流程中断

**修复难度**: ⭐⭐ (简单)

**修复方案**:
```typescript
// 创建统一错误处理
class APIError extends Error {
    constructor(public code: number, message: string) {
        super(message)
    }
}

async function handleAPIError(error: unknown) {
    if (error instanceof APIError) {
        ElMessage.error(error.message)
    } else {
        ElMessage.error("操作失败，请重试")
    }
    logger.error("API Error:", error)
}

// 使用
try {
    const res = await secretApi.availableModels()
} catch (e) {
    await handleAPIError(e)
}
```

---

### P2-7: WebSocket 无重连机制
**文件**: `web/src/views/user/index.vue`

**问题描述**:
```javascript
// ❌ 连接断开后无法恢复
let ws = new WebSocket(url)
ws.onclose = () => {}  // 无处理
```

**危害**:
- 网络波动时连接中断，无法自动恢复
- 用户无法继续对话
- 需要手动刷新页面

**修复难度**: ⭐⭐⭐ (中等)

**修复方案**:
```typescript
// composables/useWebSocket.ts
export function useWebSocket(url: string) {
    let ws: WebSocket | null = null
    let reconnectAttempts = 0
    const maxReconnectAttempts = 10
    const reconnectDelay = 3000  // 3秒
    
    function connect() {
        try {
            ws = new WebSocket(url)
            
            ws.onopen = () => {
                reconnectAttempts = 0
                emit('connected')
            }
            
            ws.onmessage = (e) => {
                emit('message', JSON.parse(e.data))
            }
            
            ws.onclose = () => {
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++
                    const delay = reconnectDelay * Math.pow(2, reconnectAttempts - 1)
                    setTimeout(connect, delay)
                }
            }
            
            ws.onerror = (e) => {
                logger.error('WebSocket error:', e)
            }
        } catch (e) {
            logger.error('WebSocket connect error:', e)
        }
    }
    
    return { connect, ws }
}
```

---

### P2-8: 日志无轮转
**文件**: `docker-compose.yml`

**问题描述**:
```yaml
# ❌ 只保留 30MB 日志（3*10MB）
logging:
    options:
        max-size: "10m"
        max-file: "3"
```

**危害**:
- 历史日志丢失
- 无法追踪事件历史
- 调试生产问题困难

**修复难度**: ⭐ (简单)

**修复方案**:
```yaml
# ✅ 增加日志保留
logging:
    driver: "json-file"
    options:
        max-size: "100m"     # 单个文件100MB
        max-file: "20"       # 保留20个文件，总2GB
        labels: "service=agenthub"

# 建议再加上日志聚合（ELK/Loki）
```

---

### P2-9: 权限检查不完整
**文件**: `backend/app/api/instances.py` (多处)

**问题描述**:
- 每个端点都手动检查 `owner_user_id`
- 容易遗漏权限检查
- 代码重复

**危害**:
- 权限漏洞风险
- 维护困难

**修复难度**: ⭐⭐ (中等)

**修复方案**:
```python
# 创建权限装饰器
async def check_resource_ownership(
    db: AsyncSession, 
    resource_type: str, 
    resource_id: int, 
    user_id: int
) -> bool:
    """检查用户是否拥有该资源"""
    if resource_type == "instance":
        result = await db.execute(
            select(AgentInstance.id).where(
                AgentInstance.id == resource_id,
                AgentInstance.owner_user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None
    return False

def require_ownership(resource_type: str, resource_id_param: str = "resource_id"):
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            resource_id = kwargs.get(resource_id_param)
            user_id = request.state.user_id
            
            async with AsyncSession(...) as db:
                if not await check_resource_ownership(db, resource_type, resource_id, user_id):
                    raise HTTPException(status_code=403)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# 使用
@router.delete("/{instance_id}")
@require_ownership("instance", "instance_id")
async def delete_instance(request: Request, instance_id: int):
    # ...
```

---

### P2-10: 敏感信息泄露
**文件**: `backend/app/api/instances.py:19-31`

**问题描述**:
- API 响应中 mask 敏感值弱
- `v[:4] + "****"` 可能仍泄露信息

**危害**:
- API Key 可能被部分暴露
- Base URL 可能被猜测

**修复难度**: ⭐⭐ (简单)

**修复方案**:
```python
def mask_sensitive_fields(data: dict) -> dict:
    """完全 mask 敏感字段"""
    sensitive_keys = (
        "key", "secret", "password", "token", 
        "url", "endpoint", "api", "base_url"
    )
    
    result = {}
    for k, v in data.items():
        if any(kw in k.lower() for kw in sensitive_keys):
            result[k] = "***"  # 完全隐藏
        else:
            result[k] = v
    return result
```

---

### P2-11: 缺少 API 速率限制
**文件**: 全局

**问题描述**:
- 没有 API 速率限制
- 可通过暴力攻击尝试登录

**危害**:
- 暴力破解风险
- DoS 攻击风险

**修复难度**: ⭐⭐ (中等)

**修复方案**:
```bash
# 安装 slowapi
pip install slowapi

# 使用
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    # ...
```

---

### P2-12: 事务隔离级别未配置
**文件**: `backend/app/models/base.py`

**问题描述**:
- 默认 READ_COMMITTED 隔离级别
- 可能导致幽灵读问题
- 没有显式事务管理

**危害**:
- 数据一致性问题

**修复难度**: ⭐⭐ (中等)

**修复方案**:
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    isolation_level="SERIALIZABLE",  # 最严格
)
```

---

## 🟡 P3（中优先级）问题清单

### P3-1: 端口分配策略低效
**文件**: `backend/app/services/instance_service.py:26-37`

**问题**: O(n) 复杂度，没有端口池预留

**修复难度**: ⭐⭐

**工作量**: 2-3 小时

---

### P3-2: 容器启动超时无限制
**文件**: `backend/app/services/instance_service.py:166-192`

**问题**: Docker 启动可能无限期等待

**修复难度**: ⭐⭐

**工作量**: 1-2 小时

---

### P3-3: 模型配置版本管理缺失
**文件**: `backend/app/models/instance.py`

**问题**: 无法查询配置变更历史

**修复难度**: ⭐⭐⭐

**工作量**: 3-4 小时

---

### P3-4: 资源限制不完整
**文件**: `backend/app/adapters/docker_adapter.py`

**问题**: 仅限制 CPU/内存，未限制：
- I/O 操作数
- 网络带宽
- 进程数量
- 磁盘大小

**修复难度**: ⭐⭐⭐

**工作量**: 4-5 小时

---

### P3-5: API 响应格式混乱
**文件**: 多个 API 文件

**问题**: 
- 有时返回 code，有时返回 status
- 有时返回 message，有时返回 error
- 无统一格式

**修复难度**: ⭐⭐⭐

**工作量**: 3-4 小时

---

## 📋 总体修复路线图

### Phase 1: 立即修复 (1-2周)
- [ ] P2-1: 容器创建竞态 (2h)
- [ ] P2-2: 启动失败恢复 (4h)
- [ ] P2-4: WebSocket 连接限制 (3h)
- [ ] P2-8: 日志轮转 (1h)
- [ ] P2-11: API 速率限制 (2h)

**小计**: 12 小时

### Phase 2: 重要功能 (2-4周)
- [ ] P2-3: 模型查询优化 (2h)
- [ ] P2-5: 前端组件拆分 (6h)
- [ ] P2-6: 前端错误处理 (3h)
- [ ] P2-7: WebSocket 重连 (3h)
- [ ] P2-9: 权限检查 (3h)

**小计**: 17 小时

### Phase 3: 完善功能 (4-6周)
- [ ] P2-10: 敏感信息保护 (2h)
- [ ] P2-12: 事务隔离 (2h)
- [ ] P3-1 至 P3-5: 性能优化 (15-20h)

**小计**: 19-24 小时

---

## ✅ 修复优先级建议

**本周优先**:
1. P2-4: WebSocket 连接限制 (安全)
2. P2-11: API 速率限制 (安全)
3. P2-1: 并发竞态 (功能)

**下周优先**:
4. P2-2: 启动失败恢复 (可靠性)
5. P2-5: 前端拆分 (可维护性)
6. P2-7: WebSocket 重连 (用户体验)

**后续**: P3 问题（性能优化）

---

## 📞 实施建议

### 开发策略
- 每个 P2 创建独立分支
- 配套单元测试
- 本地测试后再合并

### 测试策略
- P2-1: 并发测试（10+ 并发请求）
- P2-2: 容器启动超时测试
- P2-4: 连接限制测试（打开 N 个连接）
- P2-7: 网络中断模拟测试

### 部署策略
- 灰度部署（先部署到开发环境）
- 逐步推向测试/生产
- 监控新增错误率

---

**下一步**: 
1. ✅ P1 修复方案已完成
2. ⏳ P2 开始实施（本周优先 P2-4, P2-11, P2-1）
3. 📅 P3 缓后续迭代

