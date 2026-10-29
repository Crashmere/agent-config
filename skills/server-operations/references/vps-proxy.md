# Personal Proxy on `vps`

`vps` runs one Xray-core service providing VLESS + REALITY + Vision on TCP 443. The user uses Hiddify on iOS, iPadOS, Android, macOS, and Windows. All devices share one random UUID and REALITY short ID; there is no account system, subscription endpoint, management panel, domain, or separately issued TLS certificate. Business applications remain on `ali`; `nas` is unchanged.

## Runtime and Configuration

| Item | Contract |
| --- | --- |
| Binary | `/usr/local/bin/xray`, root-owned 0755; official `XTLS/Xray-core` Linux x86-64 release archive, verified against its published SHA-256 |
| Service | `/etc/systemd/system/xray.service`, enabled at boot; dedicated `xray:xray` system identity with no login shell |
| Configuration | `/etc/xray/config.json`, root:xray 0640 inside root:xray 0750 `/etc/xray` |
| Exposure | Firewalld public zone allows SSH and TCP 443; no HTTP, UDP proxy, or management port |
| REALITY target | `www.nvidia.com:443`, SNI `www.nvidia.com`; verified TLS 1.3 and ALPN `h2` from `vps` at installation |
| Outbound access | IPv4 Internet exit; explicit loopback, private, link-local, multicast, and reserved CIDRs are blocked, including cloud metadata addresses |
| Logs | Access logging disabled; warning/error output goes to the journal |
| Privileges | Only `CAP_NET_BIND_SERVICE`; read-only system/home protection, private temporary directory/devices, and no privilege escalation |

Configuration sources are [the unit](../assets/vps/xray.service), [the configuration template](../assets/vps/xray-config.json.template), and [the firewall zone](../assets/vps/public.xml). [The renderer](../scripts/render-vps-proxy.py) generates private server/client files with an official Xray binary and refuses to overwrite an output directory. [The initial installer](../scripts/install-vps-proxy.sh) accepts a reviewed staging directory, version, and archive SHA-256; it refuses to replace an existing service. Use `software-installation` for future binary updates. Distribution security updates do not update this standalone binary.

## Hiddify Import and Routing

Private materials on the maintenance Mac are under `~/vps/proxy/`, outside Git, with owner-only directory permissions. `hiddify/node.txt` and `hiddify/node-qr.png` contain the same VLESS connection; `hiddify/hiddify-options.json` contains client settings without credentials. Private server configuration and the manual recovery archive belong in `private-server/`, not in the client import directory. Never publish the link, QR, UUID, REALITY private key, or recovery archive.

Import the node by QR or through Hiddify's clipboard import. In the official tagged v4.1.1 UI, the settings import is under Settings -> upper-right three-dot menu -> Import -> Import options from file (`设置` -> three-dot menu -> `导入` -> `从文件导入选项`). The adjacent clipboard option accepts the same JSON. These are separate imports: a node URI does not carry app routing/DNS preferences. The settings select region `cn`, VPN/TUN mode, IPv4 only, remote DoH at `https://1.1.1.1/dns-query`, direct DNS at `udp://223.5.5.5`, and no LAN access to the local proxy. Hiddify's built-in LAN and region bypass rules provide direct access; unmatched traffic uses the proxy in rule mode. On an existing customized client, inspect its rule order and enabled bypass rules after import. macOS/Windows may request helper or administrator authorization for VPN/TUN, and Apple mobile platforms request permission to add a VPN configuration.

The implementation was checked against official Hiddify source for URI support, preference import keys, and built-in LAN/China bypass rules; the nested settings import menu was verified against tagged v4.1.1. Identify the user's actual platform and installed version before giving a different UI path. Actual Hiddify version behavior, rule downloads, TUN permissions, and routing on the user's five platforms require device acceptance. If necessary, configure region China, the two DNS resolvers, and VPN mode manually rather than adding a conversion or subscription service.

## Checks and Maintenance

```sh
ssh vps 'runuser -u xray -- /usr/local/bin/xray run -test -config /etc/xray/config.json'
ssh vps 'systemctl is-active xray; systemctl is-enabled xray'
ssh vps 'journalctl -u xray --no-pager -n 30'
ssh vps 'ss -ltnp "sport = :443"; firewall-cmd --zone=public --list-all'
```

Installation used Xray 26.10.21. From the maintenance Mac, an authenticated local Xray client completed HTTPS and DoH requests through the public endpoint, and its observed exit matched `vps`. A loopback destination request was blocked. An ordinary TLS connection without REALITY credentials reached the configured target rather than an authenticated proxy. Public TCP 443 reachability was verified; the provider's complete filtering rules and bandwidth/quotas were not audited. The QR was decoded locally to confirm it matches the node URI. These checks do not establish long-term availability or throughput on every user network.

For a Hiddify timeout, first check the service and repeat one authenticated request from the maintenance Mac. Then obtain the affected platform, installed Hiddify version, and client log around connection startup to distinguish profile parsing, core startup, TUN permission, network reachability, REALITY handshake, and connection-test failures. Access logging is disabled, so an empty warning/error journal does not prove that the client never reached `vps`. An Xray-to-Xray success does not verify Hiddify's URI parser or bundled core; reproduce with the affected client/core when compatibility is in question. Do not rotate credentials or change ports without evidence pointing to those settings.

For an update, download an official architecture-matched release, verify SHA-256, retain the existing binary/configuration/unit in a root-private recovery directory, run the new binary's configuration check as `xray`, replace the binary, restart only `xray.service`, and verify a real proxy request. Restore the saved binary and restart if the new release fails. Do not regenerate UUIDs or keys during an ordinary update. Keep the source template/unit aligned with any configuration changes.

## Recovery and Credential Rotation

Root-private `/root/maintenance-backups/vps-proxy-*` directories retain the pre-change firewall zone, installed version, and a recovery archive of the installed configuration, unit, and firewall zone. A copy of the recovery archive was downloaded to `~/vps/proxy/private-server/`; this is a manual off-host configuration backup, not a scheduled backup or a binary/system image. There is no business data or application database on `vps`.

To recover elsewhere, install a verified official binary, recreate the `xray` system user and directory permissions, restore the private configuration and maintained unit, run a configuration check, enable the service, and authorize/open TCP 443 on the new host/provider. A different server address requires a new client URI/QR; existing UUID/key material can remain if uncompromised. Never copy a firewall zone wholesale onto a host with other services.

To disable this proxy without affecting SSH, stop/disable `xray.service` and remove only TCP 443 from both runtime and permanent public-zone rules. Preserve configuration and backups until their deletion is explicitly authorized. A compromised shared node credential requires changing the UUID (and short ID if appropriate), updating the private client URI/QR, and reimporting on every device. Rotate REALITY key material as well if the server private key was exposed; future per-device UUIDs can provide selective revocation.
