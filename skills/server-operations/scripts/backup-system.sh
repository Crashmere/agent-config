#!/usr/bin/env bash
# Run on the maintenance computer after the agent checks and mounts the authorized external disk.
set -euo pipefail
[[ $# == 1 ]] || { echo "Usage: $0 nas|vps" >&2; exit 64; }
case $1 in
  nas) nas=nas ;;
  vps) nas=nas-via-vps ;;
  *) echo "Select nas (LAN) or vps (NAS management through VPS)." >&2; exit 64 ;;
esac
vps=vps
tool=/opt/server-recovery
receipt=$(mktemp)
trap 'rm -f "$receipt"' EXIT
ssh -T -o BatchMode=yes "$vps" "$tool gateway-stream /etc/nginx /etc/letsencrypt /etc/ssh /root/.ssh /etc/firewalld /etc/vps-proxy /etc/systemd/system /etc/cron.d /etc/passwd /etc/group /usr/local/bin/sing-box /opt/server-recovery /opt/server-context /opt/AGENTS.md" |
  ssh -T -o BatchMode=yes "$nas" "$tool receive-gateway" > "$receipt"
stage=$(<"$receipt")
[[ $stage =~ ^gateway-[A-Za-z0-9-]{1,100}$ ]] || { echo "Invalid staging receipt; inspect NAS staging." >&2; exit 65; }
# pipefail prevents acknowledgement when either producer or receiver failed.
ssh -n -T -o BatchMode=yes "$nas" "$tool accept-gateway $stage"
unit="agent-system-backup-$stage"
ssh -n -T -o BatchMode=yes "$nas" "systemd-run --unit=$unit --collect --property=Type=exec --property=MemoryMax=2G --property=Environment=GOMEMLIMIT=1536MiB --property=Nice=10 $tool backup --gateway-stage $stage"
printf 'Started NAS job %s. Monitor with: ssh %s journalctl -u %s --no-pager\n' "$unit" "$nas" "$unit"
