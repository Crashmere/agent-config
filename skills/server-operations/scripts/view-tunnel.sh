#!/usr/bin/env bash
# Run locally: map the server's loopback-only HTTP inspection endpoint through an SSH tunnel so agents can view real production pages.
# Usage: view-tunnel.sh [start | stop | status]. The default is start; reuse an existing healthy tunnel.
#   Open http://127.0.0.1:<port>/<application-name>/, for example /ledger/.
# Environment: VIEW_HOST (default: vps), VIEW_PORT (default: 18180).
set -euo pipefail

host=${VIEW_HOST:-vps}
port=${VIEW_PORT:-18180}
forward="127.0.0.1:$port:127.0.0.1:80"

healthy() { curl -fs -o /dev/null --max-time 5 "http://127.0.0.1:$port/ledger/healthz"; }
tunnel_pids() { pgrep -f "ssh .*-L $forward $host\$" || true; }
stop() { pids=$(tunnel_pids); [ -z "$pids" ] || kill $pids; }

case ${1:-start} in
  start)
    if healthy; then echo "ready http://127.0.0.1:$port/"; exit 0; fi
    stop
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "port $port is in use by another process; retry with a different VIEW_PORT" >&2; exit 1
    fi
    ssh -fN -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
      -L "$forward" "$host"
    for _ in 1 2 3 4 5; do healthy && { echo "ready http://127.0.0.1:$port/"; exit 0; }; sleep 1; done
    echo "the tunnel was established, but the inspection endpoint did not respond" >&2; exit 1 ;;
  stop) stop; echo "stopped" ;;
  status) healthy && echo "available http://127.0.0.1:$port/" || { echo "unavailable"; exit 1; } ;;
  -h|--help) sed -n '2,5p' "$0" ;;
  *) echo "unknown argument: $1" >&2; exit 2 ;;
esac
