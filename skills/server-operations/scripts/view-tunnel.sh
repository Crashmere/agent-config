#!/usr/bin/env bash
# 在本地运行：经 SSH 隧道把服务器仅回环可达的 HTTP 检查入口映射到本机，供 agent 查看线上真实页面。
# 用法：view-tunnel.sh [start | stop | status]，默认 start；已有可用隧道时直接复用。
#   打开 http://127.0.0.1:<端口>/<应用名>/，例如 /ledger/。
# 环境变量：VIEW_HOST（默认 ali）、VIEW_PORT（默认 18180）。
set -euo pipefail

host=${VIEW_HOST:-ali}
port=${VIEW_PORT:-18180}
forward="127.0.0.1:$port:127.0.0.1:80"

healthy() { curl -fs -o /dev/null --max-time 5 "http://127.0.0.1:$port/ledger/healthz"; }
tunnel_pids() { pgrep -f "ssh .*-L $forward $host\$" || true; }
stop() { pids=$(tunnel_pids); [ -z "$pids" ] || kill $pids; }

case ${1:-start} in
  start)
    if healthy; then echo "已就绪 http://127.0.0.1:$port/"; exit 0; fi
    stop
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "端口 $port 被其他进程占用，换 VIEW_PORT 重试" >&2; exit 1
    fi
    ssh -fN -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
      -L "$forward" "$host"
    for _ in 1 2 3 4 5; do healthy && { echo "已就绪 http://127.0.0.1:$port/"; exit 0; }; sleep 1; done
    echo "隧道已建立但检查入口无响应" >&2; exit 1 ;;
  stop) stop; echo "已关闭" ;;
  status) healthy && echo "可用 http://127.0.0.1:$port/" || { echo "不可用"; exit 1; } ;;
  -h|--help) sed -n '2,5p' "$0" ;;
  *) echo "未知参数：$1" >&2; exit 2 ;;
esac
