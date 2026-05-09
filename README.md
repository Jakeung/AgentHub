# 🤖 AgentHub - AI Agent 管理平台

一个功能完整的 AI Agent 管理和对话平台，支持多个 AI 模型和提供商。

---

## 📋 快速导航

### 🚀 快速开始
- **本地开发**: 查看 [`QUICKSTART.md`](QUICKSTART.md) (5 分钟快速启动)
- **详细开发指南**: 查看 [`doc/09-本地开发.md`](doc/09-本地开发.md)
- **生产部署**: 查看 [`doc/08-部署指南.md`](doc/08-部署指南.md)

### 📚 项目文档
- **项目总览**: [`doc/00-总览.md`](doc/00-总览.md)
- **数据库设计**: [`doc/01-数据库设计.md`](doc/01-数据库设计.md)
- **认证与权限**: [`doc/02-认证与权限.md`](doc/02-认证与权限.md)
- **实例管理**: [`doc/03-实例管理.md`](doc/03-实例管理.md)
- **对话与模型**: [`doc/04-对话与模型.md`](doc/04-对话与模型.md)
- **渠道管理**: [`doc/05-渠道管理.md`](doc/05-渠道管理.md)
- **运维与审计**: [`doc/06-运维与审计.md`](doc/06-运维与审计.md)
- **安全与规范**: [`doc/07-安全与规范.md`](doc/07-安全与规范.md)

### 🔧 优化与改进
- **代码优化报告**: [`doc/10-代码优化报告.md`](doc/10-代码优化报告.md) (最新优化总结)
- **自动化部署脚本**: [`deploy.sh`](deploy.sh) (生产环境一键部署)

---

## 🎯 项目特性

- ✅ **多模型支持** - 支持 DeepSeek、OpenAI、Anthropic 等多个 AI 提供商
- ✅ **实例管理** - 创建和管理独立的 AI Agent 实例
- ✅ **完整认证** - JWT 认证、角色权限管理
- ✅ **实时对话** - WebSocket 实时聊天，支持流式响应
- ✅ **审计日志** - 完整的操作审计追踪
- ✅ **易于部署** - Docker Compose 一键启动，支持自动化脚本

---

## 💻 技术栈

| 组件 | 技术 |
|------|------|
| **后端** | FastAPI + SQLAlchemy + SQLite |
| **前端** | Vue 3 + TypeScript + Vite + Element Plus |
| **容器** | Docker + Docker Compose |
| **认证** | JWT + BCrypt |

---

## 🚀 快速开始

### 方式 1: Docker Compose (推荐)
```bash
# 复制环境配置
cp .env.example .env

# 启动所有服务
docker-compose up

# 访问应用
# 前端: http://localhost
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 方式 2: 本地开发
```bash
# 后端 (终端 1)
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端 (终端 2)
cd web
npm install
npm run dev
```

### 方式 3: 生产部署 (腾讯云)
```bash
# 登录服务器
ssh ubuntu@<your-server-ip>

# 部署
cd ~/agenthub
cp .env.example .env
# 编辑 .env，修改 JWT_SECRET
./deploy.sh prod
```

详见 [`doc/08-部署指南.md`](doc/08-部署指南.md)

---

## 📖 文档结构

```
doc/
├── 00-总览.md                    # 项目整体介绍
├── 01-数据库设计.md             # 数据库 schema
├── 02-认证与权限.md             # 认证流程和权限管理
├── 03-实例管理.md               # Agent 实例相关功能
├── 04-对话与模型.md             # 对话和模型支持
├── 05-渠道管理.md               # 消息渠道管理
├── 06-运维与审计.md             # 部署和审计日志
├── 07-安全与规范.md             # 安全最佳实践
├── 08-部署指南.md               # 生产部署完整指南 ⭐
├── 09-本地开发.md               # 本地开发详细指南 ⭐
└── 10-代码优化报告.md           # 最新的代码优化改进 ⭐
```

---

## 🛠️ 常用命令

```bash
# 开发
docker-compose up          # 启动所有服务
docker-compose logs -f     # 查看实时日志
docker-compose restart     # 重启服务
docker-compose down        # 停止服务

# 生产部署
./deploy.sh prod          # 部署到生产环境
./deploy.sh prod logs     # 查看部署日志
./deploy.sh prod cleanup  # 清理旧镜像

# 数据备份
cp -r data data_backup_$(date +%Y%m%d)
```

---

## 🔐 环境配置

复制 `.env.example` 为 `.env`，并修改关键配置：

```env
# 必需修改
JWT_SECRET=<生成随机值: openssl rand -hex 32>

# 根据部署环境修改
CORS_ORIGINS=http://your-ip

# 可选配置
BACKEND_PORT=8000
FRONTEND_PORT=80
LOG_LEVEL=INFO
```

---

## 📊 项目状态

- ✅ 核心功能完整
- ✅ 生产级别部署方案
- ✅ 全面的文档
- ✅ 代码优化进行中 (Phase 1 完成)

**最近优化** (2025-05-09):
- ✅ 移除未使用代码
- ✅ 实现 Repository 层模式
- ✅ 统一错误处理
- ✅ 增强日志系统

详见 [`doc/10-代码优化报告.md`](doc/10-代码优化报告.md)

---

## 🚀 后续改进方向

### Phase 2 (建议)
- [ ] 前端组件拆分 (user/index.vue)
- [ ] WebSocket 连接改进 (重连、心跳)
- [ ] 前端错误处理完善

### Phase 3 (长期)
- [ ] 为更多实体创建 Repository
- [ ] 添加单元测试覆盖
- [ ] API 常量化
- [ ] 性能优化

详见 [`doc/10-代码优化报告.md`](doc/10-代码优化报告.md#-优化路线图)

---

## 🆘 常见问题

**Q: 如何修改 JWT 密钥?**
```bash
# 生成新密钥
openssl rand -hex 32

# 编辑 .env
JWT_SECRET=<新生成的值>
```

**Q: 如何升级 SQLite 到 MySQL?**
- 见 [`doc/08-部署指南.md#未来扩展`](doc/08-部署指南.md#-未来扩展)

**Q: 如何添加 HTTPS/域名?**
- 见 [`doc/08-部署指南.md#添加-httpshttps域名`](doc/08-部署指南.md#-未来扩展)

---

## 📞 获取帮助

- 📖 查看完整文档: `doc/` 目录
- 🐛 检查日志: `docker-compose logs -f`
- 🔧 快速参考: [`QUICKSTART.md`](QUICKSTART.md)
- 💬 项目讨论: 查看 GitHub Issues

---

## 📝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing`)
3. 提交改动 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing`)
5. 开启 Pull Request

---

## 📄 许可证

本项目遵循 MIT 许可证。详见 LICENSE 文件。

---

## 👥 作者

AgentHub 开发团队

**最后更新**: 2025-05-09  
**版本**: 1.0.0

---

**开始使用**: 阅读 [`QUICKSTART.md`](QUICKSTART.md) 或 [`doc/09-本地开发.md`](doc/09-本地开发.md)

