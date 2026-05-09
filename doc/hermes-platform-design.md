# AgentHub 平台设计（完善版）

> 版本: v2.0（可评审版）
> 日期: 2026-05-08
> 参考: Data-Master 设计理念（分层架构、RBAC、统一 API、审计与安全基线、阶段化交付）

---

## 1. 设计目标

AgentHub 是一个面向团队和个人的多实例 AI Agent 托管与运维平台，核心目标：

1. 多租户隔离: 支持每个用户管理多个独立 Agent 运行实例。
2. 低门槛接入: Web 对话 + 多渠道接入（微信/Telegram/Discord/Slack）。
3. 企业级治理: 提供 RBAC、审计日志、配置加密、速率限制、可观测性。
4. 可持续演进: 先交付 FastAPI + Vue 3 + SQLite MVP，再按阶段演进到更强编排与智能运维能力。

---

## 2. 关键设计决策

### 2.1 项目本质

AgentHub 的核心是一个 **Hermes Agent 实例管理平台**：
- 被管对象: `nousresearch/hermes-agent` Docker 容器（每用户一个独立实例）
- 管理方式: 从手动 `docker run` + `.env` 文件 → Web 界面一站式管控
- 附加能力: 内置 Web Chat（代理到 Hermes 容器端口 8642）、多渠道状态查看

### 2.2 约束条件

| 约束 | 值 | 影响 |
|------|-----|------|
| 开发模式 | 1 人 + 全程 AI 辅助 | 选 AI 代码生成质量最高的语言/框架 |
| 数据库 | SQLite | 零运维、嵌入式、单文件备份 |
| 部署 | 云服务器 + Docker | 不依赖 K8s，单机 compose 即可 |
| 交付节奏 | 质量优先，不急 | 可以选成熟方案而非最快方案 |
| 核心依赖 | Docker API（容器生命周期） | 后端必须有成熟的 Docker SDK |
| 未来扩展 | 插件市场、计费（待定） | 架构需预留扩展点但不过度设计 |

### 2.3 技术路线选型（三方案对比）

| 维度 | A: FastAPI + Vue 3 | B: FastAPI + React | C: Next.js 全栈 |
|------|---------------------|--------------------|--------------------|
| 后端语言 | Python | Python | TypeScript (Node.js) |
| Docker SDK | docker-py（官方，最成熟） | docker-py（官方，最成熟） | dockerode（社区，功能全但文档弱） |
| AI 生成质量 | Python 最优 | Python 最优 | TS 次优 |
| 前端复杂度 | Vue 3 Composition API，简洁 | React Hooks，生态最大 | 内置 SSR，单体但概念多 |
| SQLite 支持 | SQLAlchemy / Tortoise ORM | SQLAlchemy / Tortoise ORM | Prisma（SQLite 支持好） |
| WebSocket 代理 | FastAPI 原生支持 | FastAPI 原生支持 | 需额外配置 |
| 1 人维护性 | 前后端分离但都轻量 | 前后端分离但都轻量 | 单仓但调试链路长 |
| 未来扩展性 | 后端加模块即可 | 后端加模块即可 | API Routes 可扩展 |

### 2.4 最优方案：FastAPI + Vue 3 + SQLite

**选型结论**：方案 A

**理由**：

1. **docker-py 是唯一正确选择**：AgentHub 的核心操作是 Docker 容器 CRUD。Python 的 `docker-py` 是 Docker 官方维护的 SDK，API 覆盖最全、文档最好、AI 生成代码最准确。Node.js 的 `dockerode` 虽然能用，但在容器资源限制、日志流、exec 等高级操作上文档和示例明显不如 docker-py。

2. **Python + AI 开发效率最高**：当前主流 LLM 对 Python 的代码生成质量显著优于其他语言，1 人 AI 辅助开发场景下这是决定性优势。

3. **Vue 3 对单人项目更友好**：Composition API 代码量少、模板直观、无需 JSX 心智负担。ElementPlus 组件库开箱即用，管理后台场景非常成熟。

4. **SQLite 零运维**：单文件数据库，备份就是复制文件，完美匹配 1 人运维场景。SQLAlchemy 2.0 对 SQLite 支持完善。

5. **演进空间充足**：后续加插件市场/计费只需在 FastAPI 后端加模块，前端加路由页面，不需要架构重构。

**技术栈清单**：

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 前端框架 | Vue 3 + Vite | 3.5+ | Composition API + TypeScript |
| UI 组件 | ElementPlus | 2.x | 管理后台标准组件库 |
| 后端框架 | FastAPI | 0.110+ | 异步、自动文档、Pydantic 校验 |
| ORM | SQLAlchemy 2.0 | 2.0+ | 支持 async + SQLite |
| 数据库 | SQLite | 3 | 嵌入式，零运维 |
| 缓存/队列 | 内存队列（MVP）→ Redis（后续） | — | MVP 阶段不引入 Redis |
| 容器管理 | docker-py | 7.x | Docker 官方 Python SDK |
| 认证 | JWT (python-jose) | — | HttpOnly Cookie |
| 部署 | Docker Compose | 3.8+ | AgentHub 自身也容器化 |

### 2.5 非目标（当前版本不做）

1. 不做跨集群 K8s 多地域调度。
2. 不做复杂计费结算系统（预留数据模型扩展点）。
3. 不做 Agent 市场与插件商业化分发（预留模块入口）。
4. 不引入 Redis（MVP 用内存队列，后续按需引入）。

---

## 3. 总体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              客户端层                                   │
│   Web Console (Vue 3) | Admin Console | Open API Client | Webhook     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTPS / WS
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              接入层                                     │
│    API Gateway (FastAPI Router) + Auth Middleware + Rate Limiter       │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              业务层                                     │
│  IAM Service | Instance Service | Chat Service | Channel Service        │
│  Model Config Service | Audit Service | Ops Monitor Service             │
└───────────────┬───────────────────────────────┬─────────────────────────┘
                │                               │
                ▼                               ▼
┌───────────────────────────────┐     ┌───────────────────────────────────┐
│          数据与缓存层          │     │             运行层                │
│ SQLite + 内存队列(MVP)         │     │ Docker Engine (docker-py)         │
│ 配置库/审计库/任务库            │     │ Hermes 实例生命周期/日志/渠道       │
└───────────────────────────────┘     └───────────────────────────────────┘
```

### 3.1 分层职责

1. 客户端层: Vue 3 + ElementPlus 页面展示、表单交互、WebSocket 对话体验。
2. 接入层: 认证、鉴权、参数校验、统一响应封装。
3. 业务层: 领域逻辑、状态机、审计写入、权限判断。
4. 数据与缓存层: 业务持久化、会话缓存、异步任务队列。
5. 运行层: 容器生命周期管理、日志汇聚、渠道连接和健康检查。

---

## 4. 功能域设计

### 4.1 身份与权限域（IAM）

1. 登录方式: 邮箱密码（MVP），微信扫码（P1），手机号验证码（P2，可选）。
2. 权限模型: RBAC（用户-角色-权限）。
3. 默认角色:
   - admin: 全量权限
   - user: 自有实例读写权限
4. 权限码规范: `module:action`
   - `instance:view`, `instance:edit`, `instance:delete`
   - `chat:use`
   - `channel:edit`
   - `apikey:edit`
   - `admin:view`, `admin:edit`
   - `audit:view`

### 4.2 实例生命周期域

状态机:

`creating -> starting -> running -> stopping -> stopped -> restarting -> error -> deleted`

支持能力:

1. 创建实例（分配容器名、端口、资源配额）。
2. 启停重启与健康探针。
3. 实例配置热更新（模型参数、系统提示词、渠道配置）。
4. 异常恢复与重试（指数退避策略）。

### 4.3 对话与渠道域

1. Web 对话: WS 流式输出，支持历史上下文。
2. 渠道接入: 微信/Telegram/Discord/Slack 统一抽象为 `ChannelAdapter`。
3. 规则控制: 白名单、私聊/群聊策略、命令触发策略。
4. 消息审计: 记录请求元信息与 token 消耗（不存储明文敏感内容）。

### 4.4 模型与密钥管理域

1. 多提供商: DeepSeek / OpenAI / Claude / 自定义 OpenAI-compatible。
2. Key 管理: 密文存储（AES-256-GCM）。
3. 模型策略:
   - 默认模型
   - 失败回退模型
   - 实例级覆盖
4. 连通性检查: 提供 `/test` API 进行 provider 健康验证。

### 4.5 运维与治理域

1. 监控面板: 实例状态、CPU/内存、失败率、消息吞吐。
2. 审计中心: 登录、配置变更、实例操作、权限变更。
3. 告警机制: 实例异常重启频繁、渠道断连、Key 调用失败率高。

---

## 5. 数据模型（评审级）

### 5.1 核心表

1. `sys_user`
2. `sys_role`
3. `sys_permission`
4. `sys_role_permission`
5. `agent_instance`
6. `instance_model_config`
7. `instance_channel_config`
8. `api_secret`
9. `instance_runtime_log`
10. `sys_operation_log`
11. `async_task`

### 5.2 关键字段建议

`agent_instance`

- `id` BIGINT PK
- `owner_user_id` BIGINT
- `name` VARCHAR(100)
- `container_name` VARCHAR(120) UNIQUE
- `port` INT
- `status` VARCHAR(20)
- `cpu_limit` DECIMAL(4,2)
- `memory_limit_mb` INT
- `health_status` VARCHAR(20)
- `created_at`, `updated_at`

`api_secret`

- `id` BIGINT PK
- `user_id` BIGINT
- `provider` VARCHAR(30)
- `secret_ciphertext` TEXT
- `secret_mask` VARCHAR(64)
- `is_default` BOOLEAN
- `status` VARCHAR(20)
- `created_at`, `updated_at`

`sys_operation_log`

- `id` BIGINT PK
- `user_id` BIGINT
- `module` VARCHAR(50)
- `action` VARCHAR(50)
- `resource_id` VARCHAR(64)
- `detail_json` JSON
- `ip` VARCHAR(64)
- `created_at` DATETIME

### 5.3 索引建议

1. `agent_instance(owner_user_id, status, updated_at DESC)`
2. `sys_operation_log(user_id, created_at DESC)`
3. `instance_runtime_log(instance_id, created_at DESC)`
4. `async_task(status, next_retry_at)`

---

## 6. API 规范（对齐 Data-Master）

### 6.1 统一响应

```json
{ "code": 0, "data": {} }
```

```json
{ "code": -3, "message": "forbidden" }
```

### 6.2 业务错误码

1. `0`: 成功
2. `-1`: 参数错误
3. `-2`: 未认证
4. `-3`: 无权限
5. `-4`: 资源不存在
6. `-5`: 服务器错误
7. `-6`: 运行时依赖不可用（Docker/Channel/Model）

### 6.3 核心 API 分组

认证:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

实例:

- `GET /api/instances`
- `POST /api/instances`
- `GET /api/instances/{id}`
- `PUT /api/instances/{id}`
- `DELETE /api/instances/{id}`
- `POST /api/instances/{id}/start`
- `POST /api/instances/{id}/stop`
- `POST /api/instances/{id}/restart`

对话与配置:

- `WS /ws/chat/{instance_id}`
- `GET/PUT /api/instances/{id}/model-config`
- `GET/PUT /api/instances/{id}/channel-config`
- `POST /api/secrets/test`

管理与审计:

- `GET /api/admin/instances`
- `GET /api/admin/users`
- `GET /api/admin/audit-logs`
- `GET /api/admin/metrics`

---

## 7. 安全与合规基线

1. 认证: JWT + HttpOnly Cookie。
2. 鉴权: 路由级 + 服务级双层权限检查。
3. CSRF: 对写请求执行 Origin/Referer 校验。
4. 输入校验: Pydantic（后端）+ ElementPlus 表单校验（前端）。
5. 密钥保护: AES-256-GCM 密文存储，接口仅返回掩码。
6. 速率限制: 登录/IP 限流，对话接口按用户+实例限流。
7. 审计: 关键操作全记录，默认保留 180 天。
8. 租户隔离: 所有实例查询必须包含 `owner_user_id = current_user`（管理员例外）。

---

## 8. 任务编排与调度

### 8.1 异步任务类型

1. `instance.start`
2. `instance.stop`
3. `instance.restart`
4. `channel.reconnect`
5. `log.compact`
6. `health.check`

### 8.2 调度策略

1. 队列模型: MVP 内存队列 → 后续可升级 Redis + Worker。
2. 重试策略: 最多 5 次，指数退避（5s/15s/45s/120s/300s）。
3. 幂等保障: 任务唯一键（`task_type + instance_id + request_id`）。
4. 死信处理: 失败入死信队列并触发告警。

### 8.3 SLA 指标

1. 实例启动 P95 < 30s。
2. Web 对话首 token 延迟 P95 < 2.5s。
3. 渠道重连恢复时间 P95 < 60s。

---

## 9. 可观测性设计

### 9.1 指标

1. 业务指标: 活跃实例数、消息量、失败率、平均 token 消耗。
2. 系统指标: CPU/内存、容器重启次数、队列积压长度。
3. 安全指标: 登录失败率、权限拒绝次数、异常来源 IP。

### 9.2 日志

1. 结构化日志: JSON 格式，包含 trace_id。
2. 日志等级: DEBUG/INFO/WARN/ERROR。
3. 关联追踪: API 请求、异步任务、容器事件统一 trace。

---

## 10. 目录结构建议

```
agenthub/
├── backend/
│   ├── app/
│   │   ├── api/               # 路由层
│   │   ├── services/          # 领域服务层
│   │   ├── repositories/      # 数据访问层
│   │   ├── models/            # ORM 模型
│   │   ├── schemas/           # 请求/响应模型
│   │   ├── middleware/        # 认证/限流/审计注入
│   │   ├── workers/           # 异步任务处理
│   │   └── adapters/          # Docker/Channel/LLM 适配
│   └── main.py
├── web/                           # Vue 3 + Vite + ElementPlus
│   ├── src/views/
│   ├── src/components/
│   ├── src/composables/           # Vue 3 组合式函数
│   ├── src/api/                   # 前端 API 封装
│   ├── src/stores/                # Pinia 状态管理
│   └── src/router/
├── data/
│   └── agenthub.db                # SQLite 数据库文件
└── docker-compose.yml
```

---

## 11. 分阶段实施路线（可评审）

### Phase 1: 基线能力（2 周）

1. 用户认证 + RBAC 最小闭环。
2. 实例 CRUD + 启停重启。
3. WebSocket 对话能力。
4. 统一 API 响应与错误码。

验收标准:

- 普通用户仅可访问自有实例。
- 管理员可查看全局实例与用户。

### Phase 2: 治理增强（2 周）

1. API Key 密文存储 + 连通性测试。
2. 审计日志中心 + 检索过滤。
3. 登录/对话限流。
4. 异步任务框架与重试机制。

验收标准:

- 关键操作均可审计追溯。
- 异常任务可重试并有告警。

### Phase 3: 渠道与运维（2-3 周）

1. 微信/Telegram/Discord/Slack 统一适配层。
2. 运维大盘（状态、性能、失败率）。
3. 健康巡检与自动恢复策略。

验收标准:

- 渠道断连可自动恢复。
- 关键 SLA 达标并可观测。

---

## 12. 风险与应对

1. 容器资源争用
   - 应对: 配额 + 启动并发限制 + 熔断。
2. 渠道协议变更
   - 应对: 适配层解耦 + 回归测试清单。
3. 模型供应商不稳定
   - 应对: 多 provider 回退 + 超时重试 + 熔断。
4. 审计数据膨胀
   - 应对: 分区表/归档策略/冷热分层。

---

## 13. 评审结论建议

当前采用 **FastAPI + Vue 3 + SQLite** 技术路线，核心围绕 Hermes Agent 容器管理场景，利用 docker-py 官方 SDK 作为运行层基石。该方案在 1 人 AI 辅助开发模式下效率最高，同时对齐 Data-Master 的治理与规范体系，为后续插件市场、计费等扩展保留清晰路径。
