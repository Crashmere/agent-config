#!/usr/bin/env bash
# 只读主机检查；不会读取业务数据、env、SSH keys 或触发发布/备份。
set -uo pipefail
if [[ $(uname -s) != Linux ]]; then
  printf 'Run on the Linux server, not on the local workstation.\n' >&2
  exit 64
fi
inspect() {
  printf '\n[%s]\n' "$1"
  shift
  "$@" || printf '(unavailable or nonzero status: %s)\n' "$1"
}
inspect time date -Is
inspect os cat /etc/os-release
inspect architecture uname -m
inspect timezone timedatectl
inspect memory free -h
inspect disk df -hT / /opt
inspect listeners ss -ltnp
inspect running-services systemctl list-units --type=service --state=running --no-pager
inspect failed-services systemctl --failed --no-pager
inspect timers systemctl list-timers --all --no-pager
inspect applications ls -la /opt
inspect nginx-sites ls -l /etc/nginx/sites-enabled /etc/nginx/app-locations
inspect firewall ufw status verbose
inspect nginx-version nginx -v
printf '\n[available-tools]\n'
for tool in git node npm go docker sqlite3 uv; do
  command -v "$tool" || true
done
printf '\nCloud security groups, app health and documentation drift require separate verification.\n'
