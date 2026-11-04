#!/usr/bin/env bash
# Run as nas-tunnel in a transient service with Restart=no and RuntimeMaxSec=24h.
set -euo pipefail

usage() {
  echo "Usage: probe-ssh-port.sh [port]" >&2
  echo "Port defaults to 2222 and must be between 1024 and 65535." >&2
  exit 2
}

[ "$#" -le 1 ] || usage
port=${1:-2222}
[[ $port =~ ^[1-9][0-9]{3,4}$ ]] && ((port >= 1024 && port <= 65535)) || usage
config=/etc/nas-tunnels/vps.conf
[ -r "$config" ] || { echo "Cannot read $config" >&2; exit 1; }

log() {
  printf '%s utc=%s %s\n' "$(date -Is)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

child=
stop() {
  trap - TERM INT
  if [ -n "$child" ]; then
    kill -TERM "$child" 2>/dev/null || true
    wait "$child" 2>/dev/null || true
    child=
  fi
  log "event=stopped port=$port"
  exit 0
}
trap stop TERM INT

attempt=0
while :; do
  attempt=$((attempt + 1))
  log "event=attempt attempt=$attempt port=$port"
  /usr/bin/ssh -NT -F "$config" -o ClearAllForwardings=yes -o LogLevel=VERBOSE -p "$port" gateway &
  child=$!
  log "event=started attempt=$attempt port=$port pid=$child"
  if wait "$child"; then status=0; else status=$?; fi
  log "event=exited attempt=$attempt port=$port pid=$child status=$status retry_seconds=30"
  child=
  sleep 30 &
  child=$!
  wait "$child"
  child=
done
