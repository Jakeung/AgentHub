# AgentHub 部署指南

## 系统要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | Ubuntu 20.04+ / CentOS 8+ / Debian 11+ |
| CPU | 2 核 |
| 内存 | 4 GB（每个 Hermes 实例额外占用约 2GB） |
| 磁盘 | 20 GB |
| Docker | 20.10+ |
| Docker Compose | v2.0+ |
| 网络 | 能访问外网（拉取镜像、调用 LLM API） |

## 架构概览

AgentHub 由 2 个核心容器组成：

```
┌─────────────────────────────────┐
│  agenthub-backend               │  前端(Vue SPA) + 后端(FastAPI)
│  端口: 80 → 8000                │  静态文件 / API / WebSocket
└──────────┬──────────────────────┘
           │ Docker API (HTTP)
┌──────────▼──────────────────────┐
│  agenthub-docker-proxy          │  Docker Socket 安全代理
│  仅暴露容器/镜像管理 API         │
└─────────────────────────────────┘
           │
   ┌───────▼───────┐
   │ hermes-xxx-001 │  按需创建的 AI Agent 实例
   │ hermes-xxx-002 │  每个用户一个独立容器
   └───────────────┘
```

## 快速部署

### 1. 安装 Docker

```bash
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
# 重新登录使 docker 组生效
```

### 2. 获取代码

**方式一：Git 克隆（推荐）**

```bash
git clone <your-repo-url> /opt/agenthub
cd /opt/agenthub
```

**方式二：本地打包上传**

在开发机上先导出镜像（可选，用于离线部署）：

```bash
bash deploy.sh _ export-images
```

打包（排除不需要的文件）：

```bash
tar czf agenthub.tar.gz \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='data' \
  --exclude='*.db' \
  --exclude='.env' \
  --exclude='__pycache__' \
  --exclude='.venv' \
  AgentHub/
```

上传到服务器并解压：

```bash
scp agenthub.tar.gz user@your-server:/opt/
ssh user@your-server
cd /opt && tar xzf agenthub.tar.gz
cd /opt/AgentHub
```

### 3. 配置环境变量

`deploy.sh` 会自动处理：首次运行时自动从 `.env.example` 生成 `.env` 并填入随机密钥。如需自定义，可手动编辑：

```bash
vim .env
```

完整配置说明：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `JWT_SECRET` | 是 | - | JWT 签名密钥，至少 32 字符 |
| `ENCRYPTION_KEY` | 是 | - | API Key 加密密钥，至少 32 字符 |
| `API_SERVER_KEY` | 是 | - | Hermes 通信密钥 |
| `CORS_ORIGINS` | 生产环境必填 | `http://localhost` | 允许的前端域名 |
| `ENVIRONMENT` | 否 | `production` | `production` 或 `development` |
| `FRONTEND_PORT` | 否 | `80` | 对外服务端口 |
| `LOG_LEVEL` | 否 | `INFO` | 日志级别 |
| `PORT_RANGE_START` | 否 | `9001` | Hermes 实例端口范围起始 |
| `PORT_RANGE_END` | 否 | `9100` | Hermes 实例端口范围结束 |

### 4. 准备 Hermes Agent 镜像

**方式一：在线拉取**

```bash
docker pull nousresearch/hermes-agent:latest
```

**方式二：离线导入（无网络环境）**

在有网络的机器上导出镜像：

```bash
bash deploy.sh _ export-images
# 镜像文件保存到 images/ 目录
```

将 `images/` 目录随部署包一起上传到服务器。`deploy.sh` 启动时会自动从 `images/` 目录导入镜像。

### 5. 一键部署

```bash
bash deploy.sh prod
```

脚本会自动完成：生成密钥 → 创建目录 → 创建网络 → 导入镜像 → 构建 → 启动 → 健康检查。

手动部署方式：

```bash
docker compose build --no-cache
docker compose up -d
```

### 6. 验证

```bash
# 检查容器状态（应该看到 2 个容器）
docker compose ps

# 检查健康状态
curl http://localhost/api/health
# 应返回: {"status":"ok"}

# 查看日志
docker compose logs -f --tail=50
```

### 7. 初始配置

打开浏览器访问 `http://<服务器IP>`

**默认管理员账号：**
- 用户名：`admin`
- 密码：`admin123`
- **请立即修改密码**

**配置 LLM：**

进入 **系统设置** → **LLM 模型配置**：

| 配置项 | DeepSeek 示例 | OpenRouter 示例 |
|--------|--------------|-----------------|
| Provider | `custom` | `openrouter` |
| 默认模型 | `deepseek-chat` | `anthropic/claude-sonnet-4` |
| Base URL | `https://api.deepseek.com/v1` | `https://openrouter.ai/api/v1` |
| API Key | 你的 DeepSeek Key | 你的 OpenRouter Key |

保存后会自动测试连接。配置成功后，用户创建的实例即可使用 AI 聊天。

## 防火墙配置

| 端口 | 用途 | 是否对外开放 |
|------|------|-------------|
| 80（或 FRONTEND_PORT） | Web 访问 | 是 |
| 9001-9100 | Hermes 实例 | 否（Docker 内部网络） |

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 80/tcp

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload
```

## 常用操作

```bash
# 查看日志
docker compose logs -f

# 仅查看后端日志
docker compose logs -f backend

# 重启服务
docker compose restart backend

# 停止所有服务
docker compose down

# 更新部署
git pull
bash deploy.sh prod

# 清理旧镜像
docker system prune -f

# 备份数据
tar czf backup_$(date +%Y%m%d).tar.gz data/

# 查看 Hermes 实例日志
docker logs hermes-<用户名>-001 --tail=50
```

## 数据目录

```
data/
├── agenthub.db              # SQLite 数据库
└── hermes/
    ├── hermes-user1-001/     # 用户实例数据
    │   ├── .env              # 实例环境变量
    │   └── config.yaml       # 模型配置
    └── hermes-user2-001/
```

**务必定期备份 `data/` 目录。**

## HTTPS 配置（生产环境推荐）

使用 Nginx 反向代理 + Let's Encrypt：

```bash
sudo apt install nginx certbot python3-certbot-nginx
```

Nginx 配置（`/etc/nginx/sites-available/agenthub`）：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

使用 HTTPS 时，更新 `.env`：

```bash
CORS_ORIGINS=https://your-domain.com
FRONTEND_PORT=8080  # 避免与 Nginx 的 80 端口冲突
```

获取证书：

```bash
sudo certbot --nginx -d your-domain.com
```

## 故障排查

**服务无法启动**
```bash
docker compose logs backend --tail=50
# 常见原因：.env 配置错误（JWT_SECRET 太短、CORS 未设置等）
```

**聊天无回复**
```bash
# 检查 Hermes 实例是否运行
docker ps --filter "name=hermes-"

# 查看实例日志
docker logs hermes-xxx-001 --tail=50

# 常见原因：LLM API Key 未配置或无效
```

**端口被占用**
```bash
ss -tlnp | grep 80
# 修改 .env 中的 FRONTEND_PORT 为其他端口（如 8080）
```

**Docker 权限错误**
```bash
sudo usermod -aG docker $USER
# 重新登录后生效
```
