# Personal Proxy on `vps`

`vps` runs one sing-box service providing VLESS + REALITY + Vision on TCP 443. The user uses Hiddify on iOS, iPadOS, Android, macOS, and Windows. All devices share one random UUID and REALITY short ID; the proxy has no account system, subscription endpoint, management panel, domain, or separately issued proxy certificate. The accepted 2026-10-30 NAS migration left this proxy and its client imports unchanged and activated an independent Nginx web gateway on HTTPS 8443. [Current-state](current-state.md) records acceptance; [NAS migration](nas-migration.md) owns application placement and shared recovery.

## Runtime and Configuration

| Item | Contract |
| --- | --- |
| Binary | `/usr/local/bin/sing-box`, root-owned 0755; official `SagerNet/sing-box` Linux x86-64 release archive, verified against its published SHA-256 |
| Service | `/etc/systemd/system/vps-proxy.service`, enabled at boot; retained dedicated `xray:xray` system identity with no login shell |
| Configuration | `/etc/vps-proxy/config.json`, root:xray 0640 inside root:xray 0750 `/etc/vps-proxy` |
| Exposure | Proxy uses TCP 443; the web migration separately adds HTTP 80/HTTPS 8443. No UDP proxy or public management port |
| REALITY target | `www.nvidia.com:443`, SNI `www.nvidia.com`; verified TLS 1.3 and ALPN `h2` from `vps` at installation |
| Outbound access | System DNS resolves destinations to IPv4 before route checks; explicit loopback, private, link-local, multicast, and reserved CIDRs are blocked, including cloud metadata addresses |
| Logs | Warning/error output goes to the journal; successful connection access records at info level are suppressed |
| Privileges | Only `CAP_NET_BIND_SERVICE`; read-only system/home protection, private temporary directory/devices, and no privilege escalation; `AF_NETLINK` permits network-interface discovery, without TUN or network-administration capabilities |

Configuration sources are [the unit](../assets/vps/vps-proxy.service), [the configuration template](../assets/vps/sing-box-config.json.template), and [the firewall zone](../assets/vps/public.xml). [The renderer](../scripts/render-vps-proxy.py) generates private server/client files with an official sing-box binary and refuses to overwrite an output directory. [The initial installer](../scripts/install-vps-proxy.sh) accepts a reviewed staging directory, version, and archive SHA-256; it refuses to replace an existing service. Use `software-installation` for future binary updates. Distribution security updates do not update this standalone binary.

The server engine is selected for compatibility with the user's App Store Hiddify 4.0 client. Xray 26.10.21 embeds a REALITY change requiring `X25519MLKEM768` before optional `X25519` in ClientHello; the official Hiddify 4.0.4 core removes `X25519MLKEM768` from its REALITY handshake. The same QR parsed correctly but that core reported `reality verification failed` against Xray. sing-box 1.14.4 accepted the unchanged credentials in both a local reproduction and a public `vps` check. See [the REALITY server change](https://github.com/XTLS/REALITY/commit/8cdf7bf9) and [the pinned Hiddify client implementation](https://github.com/hiddify/hiddify-sing-box/blob/d1403d0d5126350e1746dcbcfab4fa0b34462478/common/tls/reality_client.go). Verify the affected Hiddify core before changing server engines; an Xray-only smoke test missed this incompatibility.

## Hiddify Import and Routing

### Client configuration record

Yuyan document **833**, titled **VPS配置**, at `/yuyan/docs/833` through the active Yuyan entrance, is the canonical node connection and Hiddify settings record. Yuyan runs on NAS and is reachable through VPS web 8443, compatibility ALI, or the LAN entrance; agent operations default to the trusted VPS SSH route. The user authorized direct updates whenever connection/client settings change. Use `yuyan-doc` to edit the affected existing sections, preserve unrelated content/formatting, and trust its verified save. Its node URI and DNS settings were checked against the working configuration on 2026-10-29 and remain unchanged by cutover.

Keep rendered addresses, node credentials, and complete client links in this private document, not in agent-config or shared server-context. Resolve its URL through the configured `yuyan-doc` gateway/public-link settings, not a hardcoded public address or permanent ALI dependency. Document 833 does not contain the REALITY server private key and cannot replace server configuration recovery.

There is no maintained local `~/vps` directory: the user requested its complete deletion, including downloads, diagnostic files, derived imports, and local recovery copies. Yuyan document 833 remains the client configuration record. When exports are needed, generate the node URI, QR, or settings file in an owner-only temporary directory outside Git, update document 833 in the same configuration-change task, and remove temporary materials after delivery. Keep the REALITY server private key in active private server configuration and an explicitly captured external recovery set, not in client exports. Never publish the link, QR, UUID, private key, or recovery archive.

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

sing-box 1.14.4 was deployed on 2026-10-29. The official Hiddify 4.0.4 macOS core parsed the actual QR's URI with matching address, port, UUID, flow, SNI, public key, and short ID. That parsed outbound completed HTTPS, the default Apple HTTP connection test, and DoH through the public endpoint; the observed exit matched `vps`, and a loopback destination request was blocked. The UUID, REALITY keys, short ID, address, SNI, and public port were preserved, so existing client imports remain valid. QR round-trip decoding passed. On the same date, the user confirmed that Hiddify 4.0.0 dev on iPhone connected and worked normally on China Mobile 5G.

During 2026-10-30 gateway acceptance, the installed macOS Hiddify app version 4.1.1 supplied its actual `hiddify-core.dylib`. A separately started loopback SOCKS client using that core and the existing node completed a CA-verified public HTTPS request through VPS TCP 443, with an exit matching VPS. The live sing-box process/configuration and proxy listener remained unchanged. This tests the installed core, not the GUI, TUN permissions, or other devices; app version 4.1.1 is not a claim about the embedded core's own version. Provider bandwidth and quotas remain unverified.

For a Hiddify timeout, first check the service and repeat one authenticated request from the maintenance Mac. Then obtain the affected platform, installed Hiddify version, and client log around connection startup to distinguish profile parsing, core startup, TUN permission, network reachability, REALITY handshake, and connection-test failures. Successful connections are not logged at warning level, so an empty journal does not prove that the client never reached `vps`. Reproduce with the affected client/core when compatibility is in question. Do not rotate credentials or change ports without evidence pointing to those settings.

For an update, download an official architecture-matched release, verify SHA-256, retain the existing binary/configuration/unit in a root-private recovery directory, run the new binary's configuration check as `xray`, replace the binary, restart only `vps-proxy.service`, and verify a real Hiddify-core proxy request. Restore the saved binary and restart if the new release fails. Do not regenerate UUIDs or keys during an ordinary update. Keep the source template/unit aligned with any configuration changes.

For configuration changes, stage a private JSON file with root:xray ownership and mode 0640, validate it with `runuser -u xray -- /usr/local/bin/sing-box check -c FILE`, and replace `/etc/vps-proxy/config.json` only after validation passes. The unit has no reload action: activate changes with `systemctl restart vps-proxy.service`, then check service status and the affected client behavior. If access or client parameters changed, revise the relevant sections in Yuyan document 833 and regenerate derived import materials. Update a separately selected external recovery set when capturing one; successful live configuration alone does not establish an independent backup. Keep the `xray` runtime account: the retired Xray software is gone, but active sing-box still uses this identity.

## Recovery and Credential Rotation

The user waived an additional retained migration recovery point. Approved historical proxy/host pre-change archives and staging were removed, along with `/usr/local/bin/xray`, `/etc/xray`, and `xray.service`. Cleanup left the live proxy/Nginx processes and configuration unchanged. Preserve `/usr/local/bin/sing-box`, `/etc/vps-proxy/config.json`, `vps-proxy.service`, the active `xray:xray` identity, and live gateway/certificate/ACME/SSH/tunnel/firewall configuration. Never run another service on proxy TCP 443. There is no business data or application database on `vps`.

The first verified NAS/VPS external package includes the captured REALITY private key/configuration alongside Nginx, certificates/ACME, SSH/tunnel access, firewall, and maintained configuration; [current-state](current-state.md#manual-data-archives) owns its acceptance and limits. Yuyan client settings and the frozen ALI application installation do not provide that VPS private state. Recover from a separately selected, verified host copy; loss of all independent private copies requires new key material and updated clients. No backup or archive-pruning timer is introduced; preserve external recovery sets under their own confirmed lifecycle.

To recover elsewhere, install a verified official binary, recreate the `xray` system user and directory permissions, restore the private configuration and maintained unit, run a configuration check, enable the service, and authorize/open TCP 443 on the new host/provider. A different server address requires a new client URI/QR; existing UUID/key material can remain if uncompromised. Never copy a firewall zone wholesale onto a host with other services.

To disable this proxy after authorization, stop/disable only `vps-proxy.service` and remove only TCP 443 from both runtime and permanent public-zone rules; keep SSH and active web 80/8443 rules. Preserve configuration/backups until deletion is separately authorized. A compromised shared node credential requires changing the UUID (and short ID if appropriate), updating the private client URI/QR, and reimporting on every device. Rotate REALITY key material as well if the server private key was exposed; future per-device UUIDs can provide selective revocation.
