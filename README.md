# AgentHub

AI Agent 管理平台，基于 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 提供多用户实例管理、对话、模型配置和管理后台。

## 功能

- **实例管理** — 每个用户独立的 AI Agent 容器，支持创建、启停、升级
- **多模型支持** — DeepSeek、OpenAI、Anthropic、OpenRouter 等
- **实时对话** — WebSocket 流式响应
- **邀请码注册** — 管理员控制用户注册
- **管理后台** — 用户管理、实例监控、审计日志、系统设置
- **一键部署** — Docker Compose + 自动化脚本

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 前端 | Vue 3 + TypeScript + Element Plus |
| 容器 | Docker + Docker Compose |
| 认证 | JWT + BCrypt |

## 快速开始

### 生产部署

```bash
git clone git@github.com:Jakeung/AgentHub.git /opt/AgentHub
cd /opt/AgentHub
bash deploy.sh prod
```

脚本自动完成：安装 Docker → 生成密钥 → 拉取镜像 → 构建 → 启动。

部署完成后访问 `http://<服务器IP>`，默认管理员 `admin / admin123`。

详细部署说明见 [DEPLOY.md](DEPLOY.md)。

### 本地开发

```bash
# Docker 方式
docker compose up

# 或分别启动
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
cd web && npm install && npm run dev
```

## 常用命令

```bash
bash deploy.sh prod              # 首次部署
bash deploy.sh prod update       # 更新（自动 git pull + 增量构建）
bash deploy.sh prod update-local # 本地代码更新（跳过 git）
bash deploy.sh prod logs         # 查看日志
bash deploy.sh prod stop         # 停止服务
bash deploy.sh prod pull-hermes  # 更新 Hermes Agent 镜像
bash deploy.sh prod cleanup      # 清理旧镜像
```

## 项目结构

```
backend/              FastAPI 后端
  app/api/            API 路由
  app/models/         数据模型
  app/services/       业务逻辑
web/                  Vue 3 前端
  src/views/          页面
  src/api/            API 调用
  src/stores/         状态管理
deploy.sh             部署脚本
docker-compose.yml    容器编排
DEPLOY.md             部署指南
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `JWT_SECRET` | JWT 签名密钥 | 自动生成 |
| `ENCRYPTION_KEY` | API Key 加密密钥 | 自动生成 |
| `CORS_ORIGINS` | 允许的前端域名 | `http://localhost` |
| `FRONTEND_PORT` | 对外服务端口 | `80` |
| `PORT_RANGE_START` | 实例端口范围起始 | `9001` |
| `PORT_RANGE_END` | 实例端口范围结束 | `9100` |

首次运行 `deploy.sh` 会自动从 `.env.example` 生成 `.env` 并填入随机密钥。

## 许可证

MIT
