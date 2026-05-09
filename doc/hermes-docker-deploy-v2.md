# Hermes 多实例 Docker 部署方案（官方镜像版）

## 一、架构

```
┌─────────────────────────────────────────────────────────┐
│                     腾讯云服务器                          │
│                    (宿主机干净无 Hermes)                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   docker ps:                                           │
│   ┌──────────────────┐    ┌──────────────────┐        │
│   │ hermes-user1    │    │ hermes-user2    │        │
│   │ 端口: 9001      │    │ 端口: 9002      │        │
│   │ 数据: /data1   │    │ 数据: /data2   │        │
│   └──────────────────┘    └──────────────────┘        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 二、官方镜像说明

| 属性 | 值 |
|-------|-----|
| 镜像 | `nousresearch/hermes-agent:latest` |
| 备用 | `ghcr.io/nousresearch/hermes-agent:latest` |
| 大小 | ~2.4 GB |
| 基础 | Debian 13.4 |
| 数据目录 | `/opt/data` (映射到宿主机) |
| 端口 | 8642 (容器内) |

---

## 三、环境准备

### 1. 安装 Docker

```bash
apt-get update && apt-get install -y docker.io
systemctl start docker
```

### 2. 创建用户数据目录

```bash
mkdir -p /opt/hermes/{user1,user2}
```

---

## 四、docker-compose.yml (可选)

> ⚠️ 如果 docker-compose 不可用，使用下方 "步骤 3" 的 docker run 命令

```yaml
version: '3.8'

services:
  # ========== 用户 1 ==========
  hermes-user1:
    image: nousresearch/hermes-agent:latest
    container_name: hermes-user1
    restart: unless-stopped
    ports:
      - "9001:8642"
    volumes:
      - /opt/hermes/user1:/opt/data
    env_file:
      - ./users/user1.env
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1"

  # ========== 用户 2 ==========
  hermes-user2:
    image: nousresearch/hermes-agent:latest
    container_name: hermes-user2
    restart: unless-stopped
    ports:
      - "9002:8642"
    volumes:
      - /opt/hermes/user2:/opt/data
    env_file:
      - ./users/user2.env
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1"
```

### 步骤 3: 启动实例 (使用 docker run)

> 如果 docker-compose 不可用，使用以下命令启动：

```bash
# 用户1
docker run -d \
  --name hermes-user1 \
  --restart unless-stopped \
  -p 9001:8642 \
  -v /opt/hermes/user1:/opt/data \
  --memory 2g --cpus 1 \
  --env-file /opt/hermes-deploy/users/user1.env \
  nousresearch/hermes-agent gateway run

# 用户2
docker run -d \
  --name hermes-user2 \
  --restart unless-stopped \
  -p 9002:8642 \
  -v /opt/hermes/user2:/opt/data \
  --memory 2g --cpus 1 \
  --env-file /opt/hermes-deploy/users/user2.env \
  nousresearch/hermes-agent gateway run
```

---

## 五、用户配置文件

### user1.env

```bash
# ===== 模型配置 =====
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# ===== 微信配置 =====
WEIXIN_DM_POLICY=open

# ===== 访问控制 =====
GATEWAY_ALLOW_ALL_USERS=true
```

### user2.env

```bash
# ===== 模型配置 =====
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# ===== Telegram 配置 =====
# TELEGRAM_BOT_TOKEN=
# TELEGRAM_ALLOWED_USERS=

# ===== 访问控制 =====
GATEWAY_ALLOW_ALL_USERS=true
```

---

## 六、部署步骤

### 步骤 1: 拉取镜像 (国内)

```bash
# 华为云镜像 (推荐)
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nousresearch/hermes-agent:latest

# 重命名镜像
docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nousresearch/hermes-agent:latest nousresearch/hermes-agent:latest

# 验证
docker images | grep hermes
```

### 步骤 2: 创建用户数据目录

```bash
mkdir -p /opt/hermes/user1 /opt/hermes/user2
mkdir -p /opt/hermes-deploy/users
```

### 步骤 3: 创建配置文件

```bash
# 创建 user1.env
cat > /opt/hermes-deploy/users/user1.env << 'EOF'
DEEPSEEK_API_KEY=sk-ae48ad3a263b49d29d30353b240b7fe9
WEIXIN_DM_POLICY=open
GATEWAY_ALLOW_ALL_USERS=true
EOF

# 创建 user2.env
cat > /opt/hermes-deploy/users/user2.env << 'EOF'
DEEPSEEK_API_KEY=sk-ae48ad3a263b49d29d30353b240b7fe9
WEIXIN_DM_POLICY=open
GATEWAY_ALLOW_ALL_USERS=true
EOF
```

### 步骤 4: 启动实例

```bash
# 用户1
docker run -d \
  --name hermes-user1 \
  --restart unless-stopped \
  -p 9001:8642 \
  -v /opt/hermes/user1:/opt/data \
  --memory 2g --cpus 1 \
  --env-file /opt/hermes-deploy/users/user1.env \
  nousresearch/hermes-agent gateway run

# 用户2
docker run -d \
  --name hermes-user2 \
  --restart unless-stopped \
  -p 9002:8642 \
  -v /opt/hermes/user2:/opt/data \
  --memory 2g --cpus 1 \
  --env-file /opt/hermes-deploy/users/user2.env \
  nousresearch/hermes-agent gateway run
```

### 步骤 5: 验证运行

```bash
# 查看容器状态
docker ps

# 查看日志确认启动成功
docker logs hermes-user1
docker logs hermes-user2
```

### 步骤 6: 配置消息平台 (可选)

```bash
# 用户1 - 微信扫码登录
docker exec -it hermes-user1 hermes gateway setup
# 选择 Weixin，用微信扫码

# 用户2 - 配置 Telegram 或微信
docker exec -it hermes-user2 hermes gateway setup
```

---

## 七、管理命令

```bash
# 查看运行中的容器
docker ps

# 查看所有容器
docker ps -a

# 查看日志
docker logs -f hermes-user1
docker logs -f hermes-user2

# 重启单个实例
docker restart hermes-user1

# 停止单个实例
docker stop hermes-user1

# 删除实例 (数据不会丢失)
docker rm hermes-user1

# 更新镜像 (需先拉取，再重新创建容器)
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nousresearch/hermes-agent:latest
docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nousresearch/hermes-agent:latest nousresearch/hermes-agent:latest

# 查看资源使用
docker stats

# 进入容器 (配置消息平台)
docker exec -it hermes-user1 /bin/bash
```

---

## 八、添加新用户

1. 创建目录: `mkdir -p /opt/hermes/user3`
2. 创建配置: `vim users/user3.env`
3. 添加服务到 docker-compose.yml
4. 重新启动: `docker-compose up -d hermes-user3`
5. 配置平台: `docker exec -it hermes-user3 hermes gateway setup`

---

## 九、更新流程

```bash
# 1. 拉取最新镜像
docker-compose pull

# 2. 重启所有实例
docker-compose up -d

# 3. 检查状态
docker-compose ps
```

数据目录 `/opt/hermes/user1` 不受影响。

---

## 十、端口说明

| 用户 | 端口 | 访问地址 |
|------|------|----------|
| user1 | 9001 | http://服务器IP:9001 |
| user2 | 9002 | http://服务器IP:9002 |

---

## 十一、注意事项

1. **微信每个账号需单独扫码登录**（进入容器执行 `hermes gateway setup`）
2. **API Key 建议每个用户独立**
3. **端口不能冲突**
4. **数据定期备份** `/opt/hermes/` 目录
5. **宿主机无需安装 Hermes**（纯 Docker 运行）

---

## 十二、验证结果

> 部署完成后的状态 (2026-05-08)

```bash
$ docker ps
NAMES          STATUS         PORTS
hermes-user2   Up 4 minutes   0.0.0.0:9002->8642/tcp, [::]:9002->8642/tcp
hermes-user1   Up 4 minutes   0.0.0.0:9001->8642/tcp, [::]:9001->8642/tcp

$ ls -la /opt/hermes/
drwxr-xr-x user1/
drwxr-xr-x user2/
```

| 检查项 | 状态 |
|--------|------|
| 镜像拉取 | ✅ 成功 |
| 容器启动 | ✅ 运行中 |
| 端口映射 | ✅ 9001, 9002 |
| 数据目录 | ✅ 已创建 |
| 资源限制 | ✅ 2G 内存, 1 CPU |