# Personal Proxy on `vps`

`vps` runs one sing-box service providing VLESS + REALITY + Vision on TCP 443. The user uses Hiddify on iOS, iPadOS, Android, macOS, and Windows. All devices share one random UUID and REALITY short ID; there is no account system, subscription endpoint, management panel, domain, or separately issued TLS certificate. Business applications remain on `ali`; `nas` is unchanged.

## Runtime and Configuration

| Item | Contract |
| --- | --- |
| Binary | `/usr/local/bin/sing-box`, root-owned 0755; official `SagerNet/sing-box` Linux x86-64 release archive, verified against its published SHA-256 |
| Service | `/etc/systemd/system/vps-proxy.service`, enabled at boot; retained dedicated `xray:xray` system identity with no login shell |
| Configuration | `/etc/vps-proxy/config.json`, root:xray 0640 inside root:xray 0750 `/etc/vps-proxy` |
| Exposure | Firewalld public zone allows SSH and TCP 443; no HTTP, UDP proxy, or management port |
| REALITY target | `www.nvidia.com:443`, SNI `www.nvidia.com`; verified TLS 1.3 and ALPN `h2` from `vps` at installation |
| Outbound access | System DNS resolves destinations to IPv4 before route checks; explicit loopback, private, link-local, multicast, and reserved CIDRs are blocked, including cloud metadata addresses |
| Logs | Warning/error output goes to the journal; successful connection access records at info level are suppressed |
| Privileges | Only `CAP_NET_BIND_SERVICE`; read-only system/home protection, private temporary directory/devices, and no privilege escalation; `AF_NETLINK` permits network-interface discovery, without TUN or network-administration capabilities |

Configuration sources are [the unit](../assets/vps/vps-proxy.service), [the configuration template](../assets/vps/sing-box-config.json.template), and [the firewall zone](../assets/vps/public.xml). [The renderer](../scripts/render-vps-proxy.py) generates private server/client files with an official sing-box binary and refuses to overwrite an output directory. [The initial installer](../scripts/install-vps-proxy.sh) accepts a reviewed staging directory, version, and archive SHA-256; it refuses to replace an existing service. Use `software-installation` for future binary updates. Distribution security updates do not update this standalone binary.

The server engine is selected for compatibility with the user's App Store Hiddify 4.0 client. Xray 26.10.21 embeds a REALITY change requiring `X25519MLKEM768` before optional `X25519` in ClientHello; the official Hiddify 4.0.4 core removes `X25519MLKEM768` from its REALITY handshake. The same QR parsed correctly but that core reported `reality verification failed` against Xray. sing-box 1.14.4 accepted the unchanged credentials in both a local reproduction and a public `vps` check. See [the REALITY server change](https://github.com/XTLS/REALITY/commit/8cdf7bf9) and [the pinned Hiddify client implementation](https://github.com/hiddify/hiddify-sing-box/blob/d1403d0d5126350e1746dcbcfab4fa0b34462478/common/tls/reality_client.go). Verify the affected Hiddify core before changing server engines; an Xray-only smoke test missed this incompatibility.

## Hiddify Import and Routing

Private materials on the maintenance Mac are under `~/vps/proxy/`, outside Git, with owner-only directory permissions. `hiddify/node.txt` and `hiddify/node-qr.png` contain the same VLESS connection; `hiddify/hiddify-options.json` contains client settings without credentials. Private server configuration and the manual recovery archive belong in `private-server/`, not in the client import directory. Never publish the link, QR, UUID, REALITY private key, or recovery archive.

Import the node by QR or through Hiddify's clipboard import. In the official tagged v4.1.1 UI, the settings import is under Settings -> upper-right three-dot menu -> Import -> Import options from file (`设置` -> three-dot menu -> `导入` -> `从文件导入选项`). The adjacent clipboard option accepts the same JSON. These are separate imports: a node URI does not carry app routing/DNS preferences. The settings select region `cn`, VPN/TUN mode, IPv4 only, remote DoH at `https://1.1.1.1/dns-query`, direct DNS at `udp://223.5.5.5`, and no LAN access to the local proxy. Hiddify's built-in LAN and region bypass rules provide direct access; unmatched traffic uses the proxy in rule mode. On an existing customized client, inspect its rule order and enabled bypass rules after import. macOS/Windows may request helper or administrator authorization for VPN/TUN, and Apple mobile platforms request permission to add a VPN configuration.

The implementation was checked against official Hiddify source for URI support, preference import keys, and built-in LAN/China bypass rules; the nested settings import menu was verified against tagged v4.1.1. Identify the user's actual platform and installed version before giving a different UI path. Actual Hiddify version behavior, rule downloads, TUN permissions, and routing on the user's five platforms require device acceptance. If necessary, configure region China, the two DNS resolvers, and VPN mode manually rather than adding a conversion or subscription service.

## Checks and Maintenance

```sh
ssh vps 'runuser -u xray -- /usr/local/bin/sing-box check -c /etc/vps-proxy/config.json'
ssh vps 'systemctl is-active vps-proxy'
ssh vps 'systemctl is-enabled vps-proxy'
ssh vps 'journalctl -u vps-proxy --no-pager -n 30'
ssh vps 'ss -ltnp "sport = :443"'
ssh vps 'firewall-cmd --zone=public --list-all'
```

sing-box 1.14.4 was deployed on 2026-10-29. The official Hiddify 4.0.4 macOS core parsed the actual QR's URI with matching address, port, UUID, flow, SNI, public key, and short ID. That parsed outbound completed HTTPS, the default Apple HTTP connection test, and DoH through the public endpoint; the observed exit matched `vps`, and a loopback destination request was blocked. The UUID, REALITY keys, short ID, address, SNI, and public port were preserved, so existing client imports remain valid. iPhone acceptance on the user's China Mobile 5G network remains to be confirmed. Provider-wide filtering rules, bandwidth/quotas, and other device/network behavior were not audited. QR round-trip decoding passed.

For a Hiddify timeout, first check the service and repeat one authenticated request from the maintenance Mac. Then obtain the affected platform, installed Hiddify version, and client log around connection startup to distinguish profile parsing, core startup, TUN permission, network reachability, REALITY handshake, and connection-test failures. Successful connections are not logged at warning level, so an empty journal does not prove that the client never reached `vps`. Reproduce with the affected client/core when compatibility is in question. Do not rotate credentials or change ports without evidence pointing to those settings.

For an update, download an official architecture-matched release, verify SHA-256, retain the existing binary/configuration/unit in a root-private recovery directory, run the new binary's configuration check as `xray`, replace the binary, restart only `vps-proxy.service`, and verify a real Hiddify-core proxy request. Restore the saved binary and restart if the new release fails. Do not regenerate UUIDs or keys during an ordinary update. Keep the source template/unit aligned with any configuration changes.

## Recovery and Credential Rotation

Root-private `/root/maintenance-backups/vps-proxy-*` directories retain initial configuration recovery materials. `/root/maintenance-backups/vps-proxy-sing-box-*` contains the current sing-box configuration/unit/firewall recovery archive and an Xray rollback archive containing its binary, unit, and private configuration. Current sing-box configuration and recovery materials also have a manual off-host copy in `~/vps/proxy/private-server/`; this is not a scheduled backup or a system image. Retired `/usr/local/bin/xray`, `/etc/xray`, and `xray.service` remain as rollback materials; `xray.service` is stopped and disabled. Never run both services on TCP 443. There is no business data or application database on `vps`.

To recover elsewhere, install a verified official binary, recreate the `xray` system user and directory permissions, restore the private configuration and maintained unit, run a configuration check, enable the service, and authorize/open TCP 443 on the new host/provider. A different server address requires a new client URI/QR; existing UUID/key material can remain if uncompromised. Never copy a firewall zone wholesale onto a host with other services.

To disable this proxy without affecting SSH, stop/disable `vps-proxy.service` and remove only TCP 443 from both runtime and permanent public-zone rules. Preserve configuration and backups until their deletion is explicitly authorized. A compromised shared node credential requires changing the UUID (and short ID if appropriate), updating the private client URI/QR, and reimporting on every device. Rotate REALITY key material as well if the server private key was exposed; future per-device UUIDs can provide selective revocation.
