#!/usr/bin/env bash
# Transient service hooks: configure only the isolated test interface and clean it on exit.
set -euo pipefail

usage() {
  echo "Usage: wireguard-test.sh <setup|cleanup> <nas|vps> [seconds]" >&2
  exit 2
}

[ "$#" -ge 2 ] && [ "$#" -le 3 ] || usage
action=$1
role=$2
duration=${3:-86400}
case $action in setup|cleanup) ;; *) usage ;; esac
case $role in
  nas) local_address=10.77.250.2; peer_address=10.77.250.1 ;;
  vps) local_address=10.77.250.1; peer_address=10.77.250.2 ;;
  *) usage ;;
esac
[[ $duration =~ ^[0-9]+$ ]] && ((duration >= 10 && duration <= 86400)) || usage
[ "$EUID" -eq 0 ] || { echo "Requires root for the isolated network interface." >&2; exit 1; }
interface=wg-udp-test
runtime=/run/tunnel-udp-test
owner="$runtime/owner"
invocation=${INVOCATION_ID:-}
reject() { printf '%s\n' "$1" >&2; exit 1; }
icmp_rule="rule family=\"ipv4\" source address=\"$peer_address/32\" destination address=\"$local_address/32\" protocol value=\"icmp\" accept"
http_rule="rule family=\"ipv4\" source address=\"$peer_address/32\" destination address=\"$local_address/32\" port port=\"19090\" protocol=\"tcp\" accept"

if [ "$action" = cleanup ]; then
  if [ ! -f "$owner" ] || [ -L "$owner" ] || [ "$(< "$owner")" != "$role:$invocation" ]; then
    printf '%s event=udp-test-cleanup-unarmed role=%s\n' "$(date -Is)" "$role"
    exit 0
  fi
  ip link delete "$interface" 2>/dev/null || true
  nft delete table inet tunnel_udp_test 2>/dev/null || true
  if [ "$role" = vps ]; then
    firewall-cmd --zone=public --remove-port=51821/udp >/dev/null 2>&1 || true
    firewall-cmd --zone=drop --remove-rich-rule="$icmp_rule" >/dev/null 2>&1 || true
    firewall-cmd --zone=drop --remove-rich-rule="$http_rule" >/dev/null 2>&1 || true
    firewall-cmd --zone=drop --remove-interface="$interface" >/dev/null 2>&1 || true
    rm -f -- /opt/tunnel-tools/udp-probe
    rmdir /opt/tunnel-tools 2>/dev/null || true
  fi
  printf '%s event=udp-test-cleaned role=%s\n' "$(date -Is)" "$role"
  exit 0
fi

for command in wg ip nft; do command -v "$command" >/dev/null; done
[[ $invocation =~ ^[0-9a-f]{32}$ ]] || reject 'Run setup through its transient owner service.'
[ -d "$runtime" ] && [ ! -L "$runtime" ]
[ "$(stat -c '%a %U' "$runtime")" = '700 root' ]
[ -f "$runtime/wireguard.conf" ] && [ ! -L "$runtime/wireguard.conf" ]
[ "$(stat -c '%a %U' "$runtime/wireguard.conf")" = '600 root' ]
[ ! -e "$owner" ] || reject 'This runtime directory already owns a test.'
if ip link show "$interface" >/dev/null 2>&1; then reject 'Test interface already exists.'; fi
if nft list table inet tunnel_udp_test >/dev/null 2>&1; then reject 'Test guard table already exists.'; fi
[ -z "$(ip -o -4 address show | awk '$4 ~ /^10\.77\.250\./ {print}')" ]
[ -z "$(ip -4 route show exact "$peer_address/32")" ]
if [ "$role" = vps ]; then
  command -v firewall-cmd >/dev/null
  [ "$(firewall-cmd --zone=drop --list-all | awk '$1 == "target:" {print $2}')" = DROP ]
  if firewall-cmd --zone=public --query-port=51821/udp >/dev/null; then reject 'Test UDP port is already open.'; fi
  if firewall-cmd --permanent --zone=public --query-port=51821/udp >/dev/null; then reject 'Test UDP port is permanently open.'; fi
  if firewall-cmd --zone=drop --query-interface="$interface" >/dev/null; then reject 'Test interface already has a firewall binding.'; fi
  if firewall-cmd --zone=drop --query-rich-rule="$icmp_rule" >/dev/null; then reject 'Test ICMP rule already exists.'; fi
  if firewall-cmd --zone=drop --query-rich-rule="$http_rule" >/dev/null; then reject 'Test HTTP rule already exists.'; fi
fi

umask 077
# Arm rollback only after every preflight passes, before the first network change.
printf '%s:%s\n' "$role" "$invocation" > "$owner"
# The WG-only guard remains restrictive even if firewalld reloads its runtime rules.
{
  printf 'table inet tunnel_udp_test {\n chain input {\n type filter hook input priority -10; policy accept;\n'
  printf 'iifname != "%s" return\n' "$interface"
  printf 'ip saddr != %s drop\nip daddr != %s drop\n' "$peer_address" "$local_address"
  printf 'ct state established,related accept\nip protocol icmp accept\n'
  [ "$role" != vps ] || printf 'tcp dport 19090 accept\n'
  printf 'drop\n }\n chain forward {\n type filter hook forward priority -10; policy accept;\n'
  printf 'iifname "%s" drop\noifname "%s" drop\n }\n}\n' "$interface" "$interface"
} > "$runtime/guard.nft"
nft --check --file "$runtime/guard.nft"
nft --file "$runtime/guard.nft"

if [ "$role" = vps ]; then
  firewall-cmd --zone=drop --add-interface="$interface" >/dev/null
  firewall-cmd --zone=drop --add-rich-rule="$icmp_rule" --timeout="$duration" >/dev/null
  firewall-cmd --zone=drop --add-rich-rule="$http_rule" --timeout="$duration" >/dev/null
  firewall-cmd --zone=public --add-port=51821/udp --timeout="$duration" >/dev/null
fi

ip link add "$interface" type wireguard
# Ubuntu's wg profile permits stdin but restricts on-disk configuration paths.
printf '%s\n' "$(< "$runtime/wireguard.conf")" | wg setconf "$interface" /dev/stdin
ip address add "$local_address/32" dev "$interface"
ip link set "$interface" mtu 1280 up
ip route add "$peer_address/32" dev "$interface" src "$local_address"
printf '%s event=udp-test-ready role=%s interface=%s local=%s peer=%s\n' \
  "$(date -Is)" "$role" "$interface" "$local_address" "$peer_address"
