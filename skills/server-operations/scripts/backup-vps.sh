#!/usr/bin/env bash
# Run on the maintenance computer after authorizing NAS external writes.
set -euo pipefail
vps=${VPS_HOST:-vps}
nas=${NAS_HOST:-nas}
tool=/opt/server-recovery
receipt=$(mktemp)
trap 'rm -f "$receipt"' EXIT
# The agent must first verify these live roots and pause certificate/configuration writers.
# sing-box remains running: the package does not contain changing proxy traffic state.
ssh -o BatchMode=yes "$vps" "$tool gateway-stream /etc/nginx /etc/letsencrypt /etc/ssh /root/.ssh /etc/firewalld /etc/vps-proxy /etc/systemd/system /etc/cron.d /etc/passwd /etc/group /usr/local/bin/sing-box /opt/server-recovery /opt/server-context /opt/AGENTS.md" |
  ssh -o BatchMode=yes "$nas" "$tool receive-gateway" > "$receipt"
# pipefail prevents acceptance of a package if either SSH transport failed.
stage=$(<"$receipt")
[[ $stage =~ ^gateway-[A-Za-z0-9-]{1,100}$ ]] || { echo "Invalid receiver receipt; inspect external staging." >&2; exit 65; }
ssh -o BatchMode=yes "$nas" "$tool accept-gateway $stage"
