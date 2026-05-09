# ✅ 部署前检查清单

完成时间: 2025-05-09  
项目: AgentHub  
状态: 生产就绪 ✓

---

## 📋 本地开发检查

- [x] 项目克隆完成
- [x] 环境文件配置 (.env.example)
- [x] Docker Compose 配置完成
- [x] 依赖清理（删除 HelloWorld 等）
- [x] 代码结构优化

**验证命令**:
```bash
docker-compose up
# 访问: http://localhost
```

---

## 🚀 生产部署检查

### 前置检查
- [ ] 腾讯云 Ubuntu 服务器已购买
- [ ] 服务器 IP 地址已记录
- [ ] SSH 密钥已配置
- [ ] 防火墙规则已规划

### 环境配置
- [ ] `.env` 文件已复制 (cp .env.example .env)
- [ ] JWT_SECRET 已生成 (openssl rand -hex 32)
- [ ] CORS_ORIGINS 已配置为服务器 IP
- [ ] 其他环境变量已检查

**必需的 .env 配置**:
```env
JWT_SECRET=<随机值>
CORS_ORIGINS=http://<your-server-ip>
```

### Docker 环境
- [ ] Docker 已安装在服务器
- [ ] Docker Compose 已安装
- [ ] Docker daemon 已启动

**验证命令**:
```bash
ssh ubuntu@<server-ip>
docker --version
docker-compose --version
```

### 部署脚本
- [ ] deploy.sh 已上传到服务器
- [ ] deploy.sh 有执行权限 (chmod +x deploy.sh)
- [ ] .env.example 已上传

**上传方式**:
```bash
scp -r /path/to/agenthub/* ubuntu@<server-ip>:~/agenthub/
```

### 一键部署
```bash
ssh ubuntu@<server-ip>
cd ~/agenthub
./deploy.sh prod
```

---

## 🔐 安全检查 (生产环境必做)

- [ ] JWT_SECRET 已修改为安全的随机字符串（不是默认值）
- [ ] CORS_ORIGINS 已限制为实际的域名/IP（不是 *)
- [ ] 防火墙已配置（只开放必要的端口）
  - [ ] 80 (HTTP)
  - [ ] 8000 (API 后端)
  - [ ] 22 (SSH)
- [ ] 定期备份计划已制定
- [ ] 监控告警已配置 (可选)

**防火墙配置例**:
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp
sudo ufw enable
```

---

## 📊 数据库检查

- [ ] 数据目录权限正确 (data/ 文件夹)
- [ ] 备份策略已规划
  - [ ] 每日自动备份脚本
  - [ ] 备份存储位置已确定

**备份脚本例**:
```bash
#!/bin/bash
cp -r ~/agenthub/data ~/agenthub/data_backup_$(date +%Y%m%d_%H%M%S)
```

---

## ✨ 应用功能检查

### 后端 API
- [ ] API 文档可访问 (http://server:8000/docs)
- [ ] 主要端点已测试
- [ ] 错误处理正常 (返回正确的错误码)
- [ ] 日志输出正常

### 前端应用
- [ ] 前端页面可访问 (http://server)
- [ ] 登录功能正常
- [ ] 创建 Instance 正常
- [ ] 对话功能正常
- [ ] 模型切换正常

### 集成功能
- [ ] 后端和前端通信正常
- [ ] WebSocket 连接正常
- [ ] 流式响应正常
- [ ] 多用户并发正常

---

## 📈 性能检查

- [ ] 后端响应时间 < 500ms
- [ ] 前端页面加载时间 < 3s
- [ ] WebSocket 连接稳定
- [ ] 数据库查询性能正常
- [ ] 磁盘使用空间合理

**检查命令**:
```bash
docker-compose logs | grep -i "error\|exception"
du -sh data/
```

---

## 📝 文档检查

- [x] 项目 README 已创建 (README.md)
- [x] 快速参考已创建 (QUICKSTART.md)
- [x] 本地开发指南已完成 (doc/09-本地开发.md)
- [x] 部署指南已完成 (doc/08-部署指南.md)
- [x] 代码优化报告已生成 (doc/10-代码优化报告.md)
- [x] 所有文档已组织到 doc/ 目录

**文档位置**:
```
├── README.md                     主项目文档
├── QUICKSTART.md                 5分钟快速开始
├── deploy.sh                     自动化部署脚本
└── doc/
    ├── 08-部署指南.md            生产部署完整指南
    ├── 09-本地开发.md            本地开发指南
    ├── 10-代码优化报告.md        代码质量报告
    └── ... (其他项目文档)
```

---

## 🔧 维护计划

### 日常
- [ ] 监控应用日志 (docker-compose logs -f)
- [ ] 检查磁盘使用情况
- [ ] 备份数据库

### 定期 (每周)
- [ ] 检查错误日志
- [ ] 监控 API 响应时间
- [ ] 清理旧数据 (可选)

### 定期 (每月)
- [ ] 完整数据库备份
- [ ] 安全补丁检查
- [ ] 性能评估

### 定期 (每季)
- [ ] 重要数据导出备份
- [ ] 灾难恢复测试
- [ ] 容量规划评估

---

## 🎯 成功标志

部署成功的标志：

1. ✅ 前端可访问: http://server
2. ✅ 后端 API 可访问: http://server:8000
3. ✅ API 文档可访问: http://server:8000/docs
4. ✅ 用户可以登录
5. ✅ 用户可以创建实例
6. ✅ 用户可以进行对话
7. ✅ 实时消息正常显示
8. ✅ 日志输出正常

---

## 📞 常见问题排查

### 应用无法启动
```bash
docker-compose logs backend
docker-compose logs frontend
```

### 前后端无法通信
- 检查 CORS_ORIGINS 配置
- 检查防火墙规则
- 检查网络连接

### 数据丢失
- 检查 data/ 目录权限
- 检查磁盘空间
- 恢复备份数据

### 性能下降
- 清理旧日志: ./deploy.sh prod cleanup
- 检查磁盘空间
- 检查 SQLite 数据库大小

---

## ✅ 最终确认

部署前最后检查：

- [ ] 所有配置文件已检查 ✓
- [ ] 安全配置已完成 ✓
- [ ] 功能测试已通过 ✓
- [ ] 文档已完整 ✓
- [ ] 备份计划已制定 ✓
- [ ] 维护计划已制定 ✓

**准备好部署！** 🚀

---

## 🚀 部署命令 (一键启动)

```bash
# 1. 进入项目目录
ssh ubuntu@<your-server-ip>
cd ~/agenthub

# 2. 配置环境
cp .env.example .env
# 编辑 .env，修改 JWT_SECRET 和 CORS_ORIGINS

# 3. 执行部署
chmod +x deploy.sh
./deploy.sh prod

# 4. 验证部署
docker-compose ps
docker-compose logs -f

# 5. 访问应用
# http://<your-server-ip>
```

---

**最后更新**: 2025-05-09  
**部署状态**: 准备就绪 ✅

