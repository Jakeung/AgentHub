# 🚀 AgentHub 快速参考

## 本地开发 (5 分钟快速开始)

```bash
# 方式 1: 一键启动（推荐）
docker-compose up

# 方式 2: 分别运行（更灵活调试）
# 终端 1 - 后端
cd backend && python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 终端 2 - 前端
cd web
npm install
npm run dev
```

**访问地址:**
- 🌐 前端: http://localhost:5173 (或 http://localhost:80 if using docker-compose)
- 🔌 后端 API: http://localhost:8000
- 📖 API 文档: http://localhost:8000/docs

---

## 生产部署 (腾讯云 Ubuntu)

### 首次部署

```bash
# 1. 登录服务器
ssh ubuntu@<your-server-ip>

# 2. 克隆代码或上传文件到 ~/agenthub
cd ~/agenthub

# 3. 配置环境
cp .env.example .env
# 编辑 .env，修改 JWT_SECRET 和 CORS_ORIGINS

# 4. 一键部署
chmod +x deploy.sh
./deploy.sh prod

# ✓ 部署完成！
```

### 日常操作

```bash
# 查看实时日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 更新代码并重新部署
./deploy.sh prod

# 停止服务
docker-compose down

# 查看服务状态
docker-compose ps
```

---

## 必需的环境变量 (.env)

```env
# 生产环境必须改这个！
JWT_SECRET=your-random-secret-key-from-openssl-rand-hex-32

# 允许的前端来源
CORS_ORIGINS=http://your-server-ip

# 后续添加域名时改为:
# CORS_ORIGINS=https://yourdomain.com
```

**生成 JWT_SECRET:**
```bash
openssl rand -hex 32
```

---

## 常用命令速查

| 任务 | 命令 |
|------|------|
| 启动开发 | `docker-compose up` |
| 查看日志 | `docker-compose logs -f` |
| 重启服务 | `docker-compose restart` |
| 停止服务 | `docker-compose down` |
| 部署到生产 | `./deploy.sh prod` |
| 更新应用 | `./deploy.sh prod` |
| 清理空间 | `./deploy.sh prod cleanup` |
| 查看容器状态 | `docker-compose ps` |

---

## 项目文件结构速览

```
backend/          FastAPI 后端
├── app/main.py   应用入口
├── app/api/      API 路由
├── app/services/ 业务逻辑
└── requirements.txt

web/              Vue 3 前端
├── src/main.ts   入口文件
├── src/components/
└── package.json

data/             数据存储目录 (SQLite)
.env              环境变量配置
docker-compose.yml 容器编排
```

---

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| 后端无法连接 | `docker-compose logs backend` 查看错误 |
| 前端 CORS 错误 | 检查 .env 中的 CORS_ORIGINS |
| 端口被占用 | `docker-compose down` 或 `lsof -i :8000` |
| 磁盘满 | `./deploy.sh prod cleanup` |
| 忘记 JWT_SECRET | 重新运行 `openssl rand -hex 32` |

---

## 数据备份

```bash
# 备份数据库
cp -r data data_backup_$(date +%Y%m%d)

# 恢复数据库
docker-compose down
cp -r data_backup_20250509/* data/
docker-compose up -d
```

---

## 下一步

- 📖 详细开发指南: 查看 `LOCAL_DEV.md`
- 🚀 生产部署指南: 查看 `DEPLOYMENT.md`
- 📝 项目文档: 查看 `doc/` 目录

---

**更多问题？** 查看完整文档或检查 Docker 日志！

