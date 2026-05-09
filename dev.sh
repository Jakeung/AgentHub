#!/usr/bin/env bash
# ============================================================
# AgentHub 开发环境管理脚本
# Usage: ./dev.sh {start|stop|restart|status|logs}
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
WEB_DIR="$SCRIPT_DIR/web"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/.logs"

BACKEND_PORT=8000
FRONTEND_PORT=5173

mkdir -p "$PID_DIR" "$LOG_DIR"

# ─── Helpers ───

_pid_alive() {
    [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null
}

_color() {
    local color=$1; shift
    case $color in
        green)  echo -e "\033[32m$*\033[0m" ;;
        red)    echo -e "\033[31m$*\033[0m" ;;
        yellow) echo -e "\033[33m$*\033[0m" ;;
        *)      echo "$*" ;;
    esac
}

# ─── Start ───

start_backend() {
    if _pid_alive "$PID_DIR/backend.pid"; then
        _color yellow "[backend] 已在运行 (PID $(cat "$PID_DIR/backend.pid"))"
        return 0
    fi
    _color green "[backend] 启动中..."
    cd "$BACKEND_DIR"
    if [[ ! -d .venv ]]; then
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt -q
    else
        source .venv/bin/activate
    fi
    nohup uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" \
        > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$PID_DIR/backend.pid"
    sleep 1
    if _pid_alive "$PID_DIR/backend.pid"; then
        _color green "[backend] 启动成功 (PID $!, port $BACKEND_PORT)"
    else
        _color red "[backend] 启动失败，查看 $LOG_DIR/backend.log"
        return 1
    fi
}

start_frontend() {
    if _pid_alive "$PID_DIR/frontend.pid"; then
        _color yellow "[frontend] 已在运行 (PID $(cat "$PID_DIR/frontend.pid"))"
        return 0
    fi
    _color green "[frontend] 启动中..."
    cd "$WEB_DIR"
    if [[ ! -d node_modules ]]; then
        npm install -q
    fi
    nohup npx vite --host 0.0.0.0 --port "$FRONTEND_PORT" \
        > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    sleep 2
    if _pid_alive "$PID_DIR/frontend.pid"; then
        _color green "[frontend] 启动成功 (PID $(cat "$PID_DIR/frontend.pid"))"
    else
        _color red "[frontend] 启动失败，查看 $LOG_DIR/frontend.log"
        return 1
    fi
}

# ─── Stop ───

stop_backend() {
    if _pid_alive "$PID_DIR/backend.pid"; then
        local pid; pid=$(cat "$PID_DIR/backend.pid")
        kill "$pid" 2>/dev/null || true
        # Wait up to 5s for graceful shutdown
        for i in $(seq 1 10); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.5
        done
        kill -9 "$pid" 2>/dev/null || true
        rm -f "$PID_DIR/backend.pid"
        _color green "[backend] 已停止"
    else
        _color yellow "[backend] 未在运行"
        rm -f "$PID_DIR/backend.pid"
    fi
}

stop_frontend() {
    if _pid_alive "$PID_DIR/frontend.pid"; then
        local pid; pid=$(cat "$PID_DIR/frontend.pid")
        kill "$pid" 2>/dev/null || true
        for i in $(seq 1 10); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.5
        done
        kill -9 "$pid" 2>/dev/null || true
        rm -f "$PID_DIR/frontend.pid"
        _color green "[frontend] 已停止"
    else
        _color yellow "[frontend] 未在运行"
        rm -f "$PID_DIR/frontend.pid"
    fi
}

# ─── Status ───

show_status() {
    echo "=== AgentHub Dev Status ==="
    if _pid_alive "$PID_DIR/backend.pid"; then
        _color green "[backend]  运行中 (PID $(cat "$PID_DIR/backend.pid"), port $BACKEND_PORT)"
    else
        _color red "[backend]  未运行"
    fi
    if _pid_alive "$PID_DIR/frontend.pid"; then
        _color green "[frontend] 运行中 (PID $(cat "$PID_DIR/frontend.pid"), port $FRONTEND_PORT)"
    else
        _color red "[frontend] 未运行"
    fi
}

# ─── Logs ───

show_logs() {
    local service="${1:-all}"
    if [[ "$service" == "backend" || "$service" == "all" ]]; then
        echo "=== Backend Logs (last 30 lines) ==="
        tail -30 "$LOG_DIR/backend.log" 2>/dev/null || echo "(无日志)"
    fi
    if [[ "$service" == "frontend" || "$service" == "all" ]]; then
        echo "=== Frontend Logs (last 30 lines) ==="
        tail -30 "$LOG_DIR/frontend.log" 2>/dev/null || echo "(无日志)"
    fi
}

# ─── Main ───

case "${1:-help}" in
    start)
        start_backend
        start_frontend
        echo ""
        show_status
        echo ""
        _color green "访问地址: http://localhost:$FRONTEND_PORT"
        _color green "后端 API:  http://localhost:$BACKEND_PORT/docs"
        ;;
    stop)
        stop_frontend
        stop_backend
        ;;
    restart)
        stop_frontend
        stop_backend
        sleep 1
        start_backend
        start_frontend
        echo ""
        show_status
        echo ""
        _color green "访问地址: http://localhost:$FRONTEND_PORT"
        _color green "后端 API:  http://localhost:$BACKEND_PORT/docs"
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${2:-all}"
        ;;
    start-backend)
        start_backend
        ;;
    start-frontend)
        start_frontend
        ;;
    stop-backend)
        stop_backend
        ;;
    stop-frontend)
        stop_frontend
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [backend|frontend]}"
        echo ""
        echo "Commands:"
        echo "  start           启动后端 + 前端"
        echo "  stop            停止后端 + 前端"
        echo "  restart         重启后端 + 前端"
        echo "  status          查看运行状态"
        echo "  logs [service]  查看日志 (backend/frontend/all)"
        echo "  start-backend   只启动后端"
        echo "  start-frontend  只启动前端"
        echo "  stop-backend    只停止后端"
        echo "  stop-frontend   只停止前端"
        exit 1
        ;;
esac
