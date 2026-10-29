#!/usr/bin/env bash
# Install a reviewed, locally staged first Xray service on vps; never overwrite one.
set -euo pipefail
umask 077

if [[ $# != 3 ]]; then
  printf 'Usage: %s STAGING_DIR VERSION ARCHIVE_SHA256\n' "$0" >&2
  exit 2
fi
stage=$1
version=$2
digest=$3
[[ $(id -u) == 0 ]]
[[ $(uname -m) == x86_64 ]]
[[ ! -e /usr/local/bin/xray && ! -e /etc/xray && ! -e /etc/systemd/system/xray.service ]]
[[ $digest =~ ^[a-f0-9]{64}$ ]]
printf '%s  %s\n' "$digest" "$stage/Xray-linux-64.zip" | sha256sum --check --status
firewall-cmd --state
if ss -H -ltn 'sport = :443' | read -r _; then
  printf 'TCP 443 is already occupied.\n' >&2
  exit 1
fi

backup=/root/maintenance-backups/vps-proxy-$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 700 "$backup" "$stage/extracted"
install -m 600 /etc/firewalld/zones/public.xml "$backup/public-before.xml"
python3 -m zipfile -e "$stage/Xray-linux-64.zip" "$stage/extracted"
install -o root -g root -m 755 "$stage/extracted/xray" /usr/local/bin/xray
/usr/local/bin/xray version
if ! getent passwd xray >/dev/null; then
  useradd --system --user-group --no-create-home --home-dir /nonexistent --shell /sbin/nologin xray
fi
install -d -o root -g xray -m 750 /etc/xray
install -o root -g xray -m 640 "$stage/server.json" /etc/xray/config.json
install -o root -g root -m 644 "$stage/xray.service" /etc/systemd/system/xray.service
runuser -u xray -- /usr/local/bin/xray run -test -config /etc/xray/config.json
systemd-analyze verify /etc/systemd/system/xray.service
systemctl daemon-reload
systemctl enable --now xray.service
sleep 2
systemctl is-active --quiet xray.service
firewall-cmd --zone=public --add-port=443/tcp
firewall-cmd --permanent --zone=public --add-port=443/tcp
printf '%s\n' "$version" > "$backup/version"
tar -czf "$backup/recovery.tar.gz" -C / etc/xray/config.json etc/systemd/system/xray.service etc/firewalld/zones/public.xml
printf 'Recovery directory: %s\n' "$backup"
systemctl show xray.service -p ActiveState -p SubState -p User -p Group -p MemoryCurrent
firewall-cmd --zone=public --list-all
