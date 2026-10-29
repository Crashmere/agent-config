#!/usr/bin/env bash
set -euo pipefail
umask 077
root=/etc/nas-ca
ip=$(cat "$root/lan-ip")
python3 -c 'import ipaddress,sys; assert ipaddress.ip_address(sys.argv[1]).version == 4' "$ip"
[ -s "$root/ca.crt" ] && [ -s "$root/ca.key" ]
if [ -s "$root/server.crt" ] && openssl x509 -in "$root/server.crt" -checkend 2592000 -noout >/dev/null; then
    openssl x509 -in "$root/server.crt" -checkip "$ip" -noout >/dev/null && exit 0
fi
work=$(mktemp -d "$root/.renew.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
openssl req -new -newkey rsa:2048 -nodes -keyout "$work/server.key" -out "$work/server.csr" -subj /CN=nas
printf 'subjectAltName=IP:%s\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' "$ip" > "$work/extensions"
openssl x509 -req -in "$work/server.csr" -CA "$root/ca.crt" -CAkey "$root/ca.key" -CAcreateserial -days 90 -sha256 -extfile "$work/extensions" -out "$work/server.crt"
openssl verify -CAfile "$root/ca.crt" "$work/server.crt"
if [ -f "$root/server.crt" ]; then cp -p "$root/server.crt" "$work/previous.crt"; fi
if [ -f "$root/server.key" ]; then cp -p "$root/server.key" "$work/previous.key"; fi
install -m 0600 "$work/server.key" "$root/server.key"
install -m 0644 "$work/server.crt" "$root/server.crt"
if command -v nginx >/dev/null && systemctl is-active --quiet nginx; then
    if ! nginx -t; then
        [ ! -f "$work/previous.crt" ] || install -m 0644 "$work/previous.crt" "$root/server.crt"
        [ ! -f "$work/previous.key" ] || install -m 0600 "$work/previous.key" "$root/server.key"
        exit 1
    fi
    systemctl reload nginx
fi
