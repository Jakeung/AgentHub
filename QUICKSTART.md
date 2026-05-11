# AgentHub 快速参考

## 部署

```bash
git clone git@github.com:Jakeung/AgentHub.git /opt/AgentHub
cd /opt/AgentHub
bash deploy.sh prod
```

首次部署自动安装 Docker、生成密钥、构建镜像、启动服务。

## 部署后配置

1. 访问 `http://<服务器IP>`，用 `admin / admin123` 登录
2. 修改管理员密码
3. 进入 **管理后台 → 邀请码**，生成邀请码
4. 进入 **管理后台 → 系统设置**，配置 LLM API Key
5. 将邀请码发给用户，用户注册后即可使用

## 命令速查

| 操作 | 命令 |
|------|------|
| 首次部署 | `bash deploy.sh prod` |
| 更新部署 | `bash deploy.sh prod update` |
| 本地代码更新 | `bash deploy.sh prod update-local` |
| 查看日志 | `bash deploy.sh prod logs` |
| 停止服务 | `bash deploy.sh prod stop` |
| 更新 Hermes 镜像 | `bash deploy.sh prod pull-hermes` |
| 清理旧镜像 | `bash deploy.sh prod cleanup` |
| 导出镜像(离线用) | `bash deploy.sh prod export-images` |
| 备份数据 | `tar czf backup_$(date +%Y%m%d).tar.gz data/` |

## 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端
cd web
npm install
npm run dev
```

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 故障排查

| 问题 | 解决 |
|------|------|
| 服务无法启动 | `docker compose logs backend --tail=50` |
| 聊天无回复 | 检查 LLM API Key 是否配置正确 |
| 端口被占用 | 修改 `.env` 中 `FRONTEND_PORT` |
| Docker 权限错误 | `sudo usermod -aG docker $USER` 后重新登录 |
| 镜像拉取慢 | 配置 Docker 镜像加速器，见 [DEPLOY.md](DEPLOY.md) |

## 更多信息

- 完整部署指南: [DEPLOY.md](DEPLOY.md)
