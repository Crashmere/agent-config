#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 <comfy-root> [port]" >&2
  exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
COMFY_ROOT=$(cd "$1" 2>/dev/null && pwd -P) || { echo "ComfyUI root does not exist: $1" >&2; exit 1; }
PORT=${2:-8188}
ESCAPED_ROOT=$(printf '%s' "$COMFY_ROOT" | sed 's/[|&\\]/\\&/g')

case "$PORT" in
  ''|*[!0-9]*) echo "Port must be numeric: $PORT" >&2; exit 1 ;;
esac
[ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || { echo "Port is out of range: $PORT" >&2; exit 1; }
[ -f "$COMFY_ROOT/main.py" ] || { echo "main.py not found under $COMFY_ROOT" >&2; exit 1; }
[ -x "$COMFY_ROOT/.venv/bin/python" ] || { echo "Project interpreter not found: $COMFY_ROOT/.venv/bin/python" >&2; exit 1; }

STARTER="$COMFY_ROOT/start-comfyui.command"
STOPPER="$COMFY_ROOT/stop-comfyui.command"
[ ! -e "$STARTER" ] || { echo "Refusing to overwrite $STARTER" >&2; exit 1; }
[ ! -e "$STOPPER" ] || { echo "Refusing to overwrite $STOPPER" >&2; exit 1; }

sed -e "s|@COMFY_ROOT@|$ESCAPED_ROOT|g" -e "s|@PORT@|$PORT|g" <<'EOF' >"$STARTER"
#!/bin/zsh
set -eu
set -o pipefail

COMFY_ROOT="@COMFY_ROOT@"
PORT=@PORT@
PID_FILE="$COMFY_ROOT/logs/comfyui.pid"
LOG_FILE="$COMFY_ROOT/logs/comfyui.log"
URL="http://127.0.0.1:$PORT"
WATCHER_PID=

cleanup() {
  [[ -z "$WATCHER_PID" ]] || kill "$WATCHER_PID" 2>/dev/null || true
  rm -f "$PID_FILE"
}
trap cleanup EXIT INT TERM
mkdir -p "$COMFY_ROOT/logs"

if /usr/sbin/lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  EXISTING_PID=$(/usr/sbin/lsof -nP -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | /usr/bin/head -n 1)
  EXISTING_CWD=$(/usr/sbin/lsof -a -p "$EXISTING_PID" -d cwd -Fn 2>/dev/null | /usr/bin/sed -n 's/^n//p')
  if [[ "$EXISTING_CWD" == "$COMFY_ROOT" ]] && /usr/bin/curl --noproxy '*' -fsS --max-time 2 "$URL/system_stats" >/dev/null 2>&1; then
    open "$URL"
    echo "ComfyUI is already running; opened $URL."
    exit 0
  fi
  echo "Port $PORT is occupied by another service; ComfyUI was not started." >&2
  exit 1
fi

echo "$$" >"$PID_FILE"
(
  for _ in {1..180}; do
    if /usr/bin/curl --noproxy '*' -fsS --max-time 2 "$URL/system_stats" >/dev/null 2>&1; then
      open "$URL"
      exit 0
    fi
    sleep 1
  done
) &
WATCHER_PID=$!

echo "Starting ComfyUI on $URL. Press Control-C to stop."
cd "$COMFY_ROOT"
"$COMFY_ROOT/.venv/bin/python" main.py \
  --listen 127.0.0.1 \
  --port "$PORT" \
  --disable-auto-launch \
  2>&1 | /usr/bin/tee -a "$LOG_FILE"
EOF

sed -e "s|@COMFY_ROOT@|$ESCAPED_ROOT|g" -e "s|@PORT@|$PORT|g" <<'EOF' >"$STOPPER"
#!/bin/zsh
set -eu

COMFY_ROOT="@COMFY_ROOT@"
PORT=@PORT@
PID_FILE="$COMFY_ROOT/logs/comfyui.pid"
COMFY_PID=$(/usr/sbin/lsof -nP -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | /usr/bin/head -n 1 || true)

if [[ -z "$COMFY_PID" ]]; then
  rm -f "$PID_FILE"
  echo "ComfyUI is not running."
  exit 0
fi

PROCESS_CWD=$(/usr/sbin/lsof -a -p "$COMFY_PID" -d cwd -Fn 2>/dev/null | /usr/bin/sed -n 's/^n//p')
PROCESS_COMMAND=$(/bin/ps -p "$COMFY_PID" -o command=)
if [[ "$PROCESS_CWD" != "$COMFY_ROOT" || "$PROCESS_COMMAND" != *"main.py"* ]]; then
  echo "Port $PORT belongs to another process; refusing to stop PID $COMFY_PID." >&2
  exit 1
fi

kill "$COMFY_PID"
for _ in {1..20}; do
  if ! kill -0 "$COMFY_PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "ComfyUI stopped."
    exit 0
  fi
  sleep 0.25
done

echo "ComfyUI did not stop cleanly; PID $COMFY_PID is still running." >&2
exit 1
EOF

chmod +x "$STARTER" "$STOPPER"
printf 'Installed:\n  %s\n  %s\n' "$STARTER" "$STOPPER"
