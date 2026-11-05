#!/usr/bin/env bash
# Run through a transient systemd service; collect private, bounded network evidence.
set -euo pipefail

usage() {
  echo "Usage: observe-tunnels.sh <nas|vps> <new-output-directory> <seconds> <peer-ip>..." >&2
  echo "NAS peers: ALI then VPS. VPS peer: NAS public source. Maximum duration: 86400 seconds." >&2
  echo "SSH_PORTS defaults to 22; set SSH_PORTS=22,2222 for an alternate-port comparison." >&2
  exit 2
}

[ "$#" -ge 4 ] || usage
role=$1
output=$2
duration=$3
shift 3
peers=("$@")
case $role in
  nas) [ "${#peers[@]}" -eq 2 ] || usage ;;
  vps) [ "${#peers[@]}" -eq 1 ] || usage ;;
  *) usage ;;
esac
[[ $duration =~ ^[0-9]+$ ]] && ((duration >= 10 && duration <= 86400)) || usage
[[ $output == /var/log/nas-tunnel-diagnostics/* ]] || usage
for peer in "${peers[@]}"; do
  [[ $peer =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || usage
done
port_list=${SSH_PORTS:-22}
[[ $port_list =~ ^[0-9]+(,[0-9]+)*$ ]] || usage
IFS=, read -r -a ports <<< "$port_list"
for port in "${ports[@]}"; do
  [[ $port =~ ^[1-9][0-9]{0,4}$ ]] && ((port <= 65535)) || usage
done
sample_limit=16777216
[ "${#ports[@]}" -le 1 ] || sample_limit=33554432
[ ! -e "$output" ] || { echo "Output directory already exists: $output" >&2; exit 1; }
for command in tcpdump timeout head stdbuf ip ss ping curl; do
  command -v "$command" >/dev/null || { echo "Missing tool: $command" >&2; exit 1; }
done

umask 077
install -d -m 0700 "$output"
interface=$(ip -4 route get "${peers[0]}" | awk '{for (i=1;i<NF;i++) if ($i=="dev") {print $(i+1); exit}}')
[ -n "$interface" ] || { echo "Cannot determine capture interface" >&2; exit 1; }
capture_ports="(port ${ports[0]}"
nas_ports="( dport = :${ports[0]}"
vps_ports="( sport = :${ports[0]}"
for port in "${ports[@]:1}"; do
  capture_ports+=" or port $port"
  nas_ports+=" or dport = :$port"
  vps_ports+=" or sport = :$port"
done
capture_ports+=")"
nas_ports+=" )"
vps_ports+=" )"
filter="tcp and $capture_ports and (host ${peers[0]}"
for peer in "${peers[@]:1}"; do filter+=" or host $peer"; done
filter+=")"

{
  date -Is
  printf 'role=%s duration=%s interface=%s ports=%s peers=%s sample_limit=%s\n' \
    "$role" "$duration" "$interface" "$port_list" "${peers[*]}" "$sample_limit"
  ip -br address
  ip -4 route
  tcpdump --version
} > "$output/metadata.txt"

# Text summaries only: no pcap, packet-body dump, or proxy-443 capture.
# Unbuffer cap writers so low-rate traces survive the service's stop deadline.
(timeout --signal=INT --kill-after=5s "$duration" tcpdump -i "$interface" -nn -tttt -p -K -s 96 -l \
    "$filter and (tcp[tcpflags] & (tcp-syn|tcp-fin|tcp-rst) != 0)" 2>&1 \
    | stdbuf -o0 head -c 8388608 > "$output/control.txt") &
control_pid=$!
trap 'kill "$control_pid" 2>/dev/null || true; wait "$control_pid" 2>/dev/null || true' EXIT

sample_loop() {
  local deadline=$((SECONDS + duration)) previous=unknown last_burst=-60 pending_burst=none state tcp_info health router listener pid actual size remaining active_states index peer https_port https_result
  while ((SECONDS < deadline)); do
    date -Is
    state=healthy
    ip -4 route
    if [ "$role" = nas ]; then
      router=$(ip -4 route show default | awk 'NR==1 {print $3}')
      if [ -n "$router" ]; then ping -n -c 1 -W 1 "$router" || true; fi
      for index in "${!peers[@]}"; do
        peer=${peers[$index]}
        ping -n -c 1 -W 1 "$peer" || true
        https_port=443
        [ "$index" -eq 0 ] || https_port=8443
        # Fresh TLS connections distinguish SSH-only stalls from broader TCP failures.
        https_result=$(curl --noproxy '*' --http1.1 -sS --connect-timeout 2 --max-time 4 \
          -o /dev/null -w '%{http_code} connect=%{time_connect} tls=%{time_appconnect} total=%{time_total}' \
          "https://$peer:$https_port/portal/login" 2>&1) || true
        printf 'gateway_https peer=%s port=%s result=%s\n' "$peer" "$https_port" "$https_result"
      done
      systemctl show reverse-tunnel@ali.service reverse-tunnel@vps.service \
        -p Id -p MainPID -p ActiveState -p SubState -p NRestarts
      active_states=$(systemctl is-active reverse-tunnel@ali.service reverse-tunnel@vps.service || true)
      [ "$active_states" = $'active\nactive' ] || state=failed
      cat /proc/net/wireless
      tcp_info=$(ss -tinop "( $nas_ports and ( dst ${peers[0]} or dst ${peers[1]} ) )")
    else
      tcp_info=$(ss -tinop "( $vps_ports and dst ${peers[0]} )")
      listener=$(ss -H -ltnp '( sport = :18085 )')
      printf 'portal_listener=%s\n' "$listener"
      pid=$(printf '%s\n' "$listener" | sed -n 's/.*pid=\([0-9]*\),.*/\1/p')
      if [ -n "$pid" ]; then
        actual=$(ss -Htnp state established '( sport = :22 )' | awk -v id="pid=$pid," 'index($0,id) {print $4; exit}')
        printf 'nas_observed_peer=%s capture_source=%s\n' "$actual" "${peers[0]}"
        if [ -n "$actual" ] && [ "${actual%:*}" != "${peers[0]}" ]; then
          echo 'SOURCE_CHANGED: restart diagnostics with the new NAS public source.'
        fi
      fi
    fi
    printf '%s\n' "$tcp_info"
    [[ $tcp_info =~ (^|[[:space:]])retrans:[1-9][0-9]*/ ]] && state=failed
    health=$(curl -sS --connect-timeout 1 --max-time 3 -o /dev/null \
      -w '%{http_code} %{time_total}' http://127.0.0.1:18085/healthz 2>&1) || true
    printf 'portal_health=%s\n' "$health"
    [[ $health == 200\ * ]] || state=failed

    if [ "$previous" = unknown ] || { [ "$state" = failed ] && [ "$previous" != failed ]; }; then
      pending_burst=$state
    fi
    if [ "$pending_burst" != none ] && ((SECONDS - last_burst >= 60)); then
      size=0
      [ ! -f "$output/bursts.txt" ] || size=$(wc -c < "$output/bursts.txt")
      remaining=$((8388608 - size))
      if ((remaining > 0)); then
        printf 'header_burst reason=%s current_state=%s remaining_bytes=%s\n' "$pending_burst" "$state" "$remaining"
        (timeout --signal=INT --kill-after=5s 30 tcpdump -i "$interface" -nn -tttt -p -K -s 96 -l -c 120 \
            "$filter" 2>&1 | stdbuf -o0 head -c "$remaining" >> "$output/bursts.txt") &
        last_burst=$SECONDS
      fi
      pending_burst=none
    fi
    printf 'sample_state=%s\n\n' "$state"
    previous=$state
    sleep 15
  done
}

sample_loop 2>&1 | stdbuf -o0 head -c "$sample_limit" > "$output/samples.txt"
wait "$control_pid" || true
printf 'Observation complete: %s\n' "$output"
