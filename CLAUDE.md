# AgentHub

## 项目简介
多用户 AI Agent 管理平台，基于 Hermes 框架。用户通过 Web UI 创建 Agent 实例（Docker 容器），配置工具/技能，绑定微信/飞书渠道。

## 技术栈
- **后端**: Python 3.10 / FastAPI / SQLAlchemy (async) / SQLite (aiosqlite)
- **前端**: Vue 3 / TypeScript / Element Plus / Vite
- **基础设施**: Docker Compose / Docker API Proxy / agenthub-network

## 目录结构
```
backend/
  app/
    api/          # FastAPI 路由（chat, instances, tools, usage, admin_*）
    models/       # SQLAlchemy 模型（instance, tool, usage, user）
    services/     # 业务逻辑（instance_service, chat_service, usage_service）
    adapters/     # 外部集成（docker_adapter, hermes_adapter）
    core/         # 配置、异常、响应格式
  main.py         # FastAPI app 入口
web/
  src/
    api/          # Axios API 封装
    views/        # 页面组件（user/, admin/）
    components/   # 布局组件（UserLayout, AdminLayout）
    stores/       # Pinia 状态管理
    router/       # Vue Router
docker-compose.yml
deploy.sh         # 部署脚本
```

## 开发规范

### 后端
- 异步优先：所有数据库操作使用 `async/await` + `AsyncSession`
- 路由前缀：用户端 `/api/`，管理端 `/api/admin/`
- 错误处理：`BusinessError` (业务错误) / `ValidationError` (参数校验)
- 容器操作通过 `DockerAdapter`，不直接调用 docker-py

### 前端
- 组件库：Element Plus，不混用其他 UI 库
- API 封装：每个模块一个 ts 文件在 `web/src/api/`
- 路由守卫：用户端 `/user/*`，管理端 `/admin/*`，自动重定向

### 容器安全
- hermes 容器: `cap_drop: ALL` + 最小 cap_add
- `no-new-privileges: true`
- 数据目录权限由容器启动时自行 chown（不在宿主机 hardcode uid）
- 每个实例独立 `api_server_key`

## 部署
```bash
# 本地开发
cd backend && uvicorn main:app --reload
cd web && npm run dev

# 生产部署
bash deploy.sh prod update-git
# 等效于: git pull + docker compose build + docker compose up -d

# 启用 Camofox 浏览器（可选）
docker pull ghcr.io/jo-inc/camofox-browser:latest
docker compose --profile camofox up -d
```

## 关键技术决策
- **SQLite 而非 PostgreSQL**: 单节点部署，简化运维
- **共享 Camofox**: 所有实例共用一个反检测浏览器服务，通过 Docker 内网通信
- **工具 API Key 注入**: 工具配置保存时自动写入容器 .env 并重启
- **容器 self-chown**: 避免 hardcode uid，适配不同部署环境
