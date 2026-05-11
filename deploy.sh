#!/bin/bash

set -e

# AgentHub 部署脚本
# 使用方式: bash deploy.sh [prod|dev] [logs|stop|cleanup|update|pull-hermes|export-images]

ENVIRONMENT=${1:-prod}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

install_docker() {
    if command -v docker &> /dev/null; then
        return 0
    fi

    log_info "Docker 未安装，正在自动安装..."

    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq ca-certificates curl gnupg
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update -qq
        sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif command -v yum &> /dev/null; then
        sudo yum install -y yum-utils
        sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    else
        log_warn "无法自动安装 Docker，尝试通用安装脚本..."
        curl -fsSL https://get.docker.com | bash
    fi

    sudo systemctl enable docker
    sudo systemctl start docker

    if [ "$(id -u)" -ne 0 ]; then
        sudo usermod -aG docker "$USER"
        log_warn "已将当前用户加入 docker 组，可能需要重新登录"
    fi

    log_info "Docker 安装完成"
}

install_compose() {
    if docker compose version &> /dev/null 2>&1; then
        return 0
    fi
    if command -v docker-compose &> /dev/null; then
        return 0
    fi

    log_info "Docker Compose 未安装，正在安装..."

    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y -qq docker-compose-plugin 2>/dev/null || true
    elif command -v yum &> /dev/null; then
        sudo yum install -y docker-compose-plugin 2>/dev/null || true
    fi

    if ! docker compose version &> /dev/null 2>&1; then
        log_info "安装独立版 docker-compose..."
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f 4 2>/dev/null || echo "v2.27.0")
        sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose 2>/dev/null
        sudo chmod +x /usr/local/bin/docker-compose
    fi

    log_info "Docker Compose 安装完成"
}

check_docker() {
    install_docker
    install_compose

    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose 安装失败，请手动安装"
        exit 1
    fi

    log_info "Docker: $(docker --version | head -1)"
    log_info "Compose: $($COMPOSE_CMD version | head -1)"
}

check_env() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_info ".env 文件不存在，自动生成..."
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"

        JWT_SECRET=$(openssl rand -hex 32)
        ENCRYPTION_KEY=$(openssl rand -base64 32)
        API_SERVER_KEY=$(openssl rand -hex 32)

        sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" "$SCRIPT_DIR/.env"
        sed -i "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|" "$SCRIPT_DIR/.env"
        sed -i "s/^API_SERVER_KEY=.*/API_SERVER_KEY=$API_SERVER_KEY/" "$SCRIPT_DIR/.env"
        sed -i "s/^ENVIRONMENT=.*/ENVIRONMENT=production/" "$SCRIPT_DIR/.env"

        IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
        sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://$IP|" "$SCRIPT_DIR/.env"

        log_info "已自动生成密钥并写入 .env"
        log_warn "如需自定义 CORS_ORIGINS 或端口，请编辑 .env 后重新运行"
    fi
}

setup_dirs() {
    mkdir -p "$SCRIPT_DIR/data/hermes"
    chmod 755 "$SCRIPT_DIR/data"
}

setup_network() {
    if ! docker network inspect agenthub-network &> /dev/null 2>&1; then
        log_info "创建 Docker 网络 agenthub-network..."
        docker network create agenthub-network --subnet=172.20.0.0/16 || true
    fi
}

load_images() {
    IMAGES_DIR="$SCRIPT_DIR/images"
    if [ -d "$IMAGES_DIR" ]; then
        for img_file in "$IMAGES_DIR"/*.tar; do
            if [ -f "$img_file" ]; then
                log_info "导入镜像: $(basename $img_file)..."
                docker load -i "$img_file"
            fi
        done
    fi
}

HERMES_IMAGE="nousresearch/hermes-agent:latest"

ensure_hermes_image() {
    if docker image inspect "$HERMES_IMAGE" &> /dev/null; then
        log_info "Hermes Agent 镜像已存在"
        return 0
    fi

    log_info "Hermes Agent 镜像不存在，尝试导入..."
    load_images

    if docker image inspect "$HERMES_IMAGE" &> /dev/null; then
        log_info "已从本地 .tar 导入 Hermes Agent 镜像"
        return 0
    fi

    log_info "本地无 .tar 文件，从 Docker Hub 拉取..."
    if docker pull "$HERMES_IMAGE"; then
        log_info "Hermes Agent 镜像拉取成功"
    else
        log_error "Hermes Agent 镜像拉取失败，请手动执行: docker pull $HERMES_IMAGE"
        log_warn "或将镜像 .tar 文件放入 images/ 目录"
    fi
}

pull_hermes() {
    check_docker
    log_info "检查 Hermes Agent 镜像更新..."

    OLD_ID=$(docker image inspect "$HERMES_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "none")

    load_images

    if docker pull "$HERMES_IMAGE"; then
        NEW_ID=$(docker image inspect "$HERMES_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "")
        if [ "$OLD_ID" == "$NEW_ID" ]; then
            log_info "已是最新版本，无需更新"
        else
            log_info "已更新到新版本"
            log_info "旧镜像 ID: ${OLD_ID:0:19}"
            log_info "新镜像 ID: ${NEW_ID:0:19}"
            log_warn "请在管理界面通知用户升级实例"
        fi
    else
        log_error "镜像拉取失败，请检查网络或配置镜像加速器"
    fi
}

pull_code() {
    if [ "$ENVIRONMENT" == "prod" ] && [ -d "$SCRIPT_DIR/.git" ]; then
        log_info "拉取最新代码..."
        cd "$SCRIPT_DIR"
        git pull origin main || log_warn "Git 拉取失败，继续使用本地代码"
    fi
}

start_services() {
    log_info "构建镜像（前端 + 后端合并容器）..."
    $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" build --no-cache

    log_info "启动服务..."
    $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" up -d

    log_info "等待服务就绪..."
    for i in $(seq 1 15); do
        if $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" exec -T backend curl -f -s http://localhost:8000/api/health > /dev/null 2>&1; then
            log_info "服务已就绪"
            return
        fi
        sleep 2
    done
    log_warn "服务启动超时，查看日志:"
    $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" logs backend --tail=30
}

show_logs() {
    check_docker
    $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" logs -f --tail=50
}

cleanup() {
    log_info "清理旧镜像..."
    docker system prune -f
    log_info "清理完成"
}

stop_services() {
    check_docker
    $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" down
    log_info "服务已停止"
}

export_images() {
    mkdir -p "$SCRIPT_DIR/images"
    log_info "导出 Hermes Agent 镜像..."
    docker save nousresearch/hermes-agent:latest -o "$SCRIPT_DIR/images/hermes-agent.tar"
    log_info "导出 Docker Socket Proxy 镜像..."
    docker save tecnativa/docker-socket-proxy:latest -o "$SCRIPT_DIR/images/docker-socket-proxy.tar"
    log_info "镜像已导出到 images/ 目录"
    ls -lh "$SCRIPT_DIR/images/"
}

update_services() {
    log_info "====== AgentHub 更新 ======"
    check_docker
    setup_dirs

    if [ -d "$SCRIPT_DIR/.git" ]; then
        log_info "拉取最新代码..."
        cd "$SCRIPT_DIR"
        git pull origin main || { log_error "Git 拉取失败"; exit 1; }
    fi

    load_images

    log_info "重新构建镜像（增量构建）..."
    $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" build

    log_info "重启服务..."
    $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" up -d

    log_info "等待服务就绪..."
    for i in $(seq 1 15); do
        if $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" exec -T backend curl -f -s http://localhost:8000/api/health > /dev/null 2>&1; then
            log_info "服务已就绪"
            FRONTEND_PORT=$(grep -E '^FRONTEND_PORT=' "$SCRIPT_DIR/.env" 2>/dev/null | cut -d= -f2 || echo "80")
            FRONTEND_PORT=${FRONTEND_PORT:-80}
            IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
            log_info "====== 更新完成 ======"
            log_info "访问地址: http://${IP}:${FRONTEND_PORT}"
            return
        fi
        sleep 2
    done
    log_warn "服务启动超时，查看日志:"
    $COMPOSE_CMD -f "$SCRIPT_DIR/docker-compose.yml" logs backend --tail=30
}

main() {
    log_info "====== AgentHub 部署 ======"
    log_info "环境: $ENVIRONMENT"

    check_docker
    check_env
    setup_dirs
    setup_network
    ensure_hermes_image
    pull_code
    start_services

    FRONTEND_PORT=$(grep -E '^FRONTEND_PORT=' "$SCRIPT_DIR/.env" 2>/dev/null | cut -d= -f2 || echo "80")
    FRONTEND_PORT=${FRONTEND_PORT:-80}
    IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

    log_info "====== 部署完成 ======"
    log_info "访问地址: http://${IP}:${FRONTEND_PORT}"
    log_info "默认管理员: admin / admin123"
    log_info ""
    log_info "查看日志: $COMPOSE_CMD logs -f"
    log_info "停止服务: $COMPOSE_CMD down"
}

case "${2:-}" in
    logs)           show_logs ;;
    stop)           stop_services ;;
    cleanup)        cleanup ;;
    update)         update_services ;;
    pull-hermes)    pull_hermes ;;
    export-images)  export_images ;;
    *)              main ;;
esac
