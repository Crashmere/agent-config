# VPS Operations

`vps` is a separate AlmaLinux KVM VM and the active primary public web HTTPS 8443 gateway to NAS after the accepted 2026-10-30 cutover. Its sing-box proxy independently retains TCP 443; applications and authoritative data are on NAS. [Current-state](current-state.md) records acceptance and outstanding recovery/device scope, and [NAS migration](nas-migration.md) owns shared access/recovery. Resolve its address and administrator key from trusted local SSH configuration; do not put them in this public repository.

## Host and Access

The local alias is `ssh vps`, with root public-key authentication, port 22, explicit identity selection, strict host-key verification, and 30-second keepalives. The hostname is `vps`; time is Asia/Shanghai with chrony synchronization. The guest has 2 vCPU, about 1 GiB RAM, 544 MiB swap, and a 20 GiB virtual disk divided into ext4 `/boot` and `/`. Kernel and package versions are volatile; query them rather than pinning the initial image version.

The VM advertises an Intel Xeon SierraForest CPU model. Its virtual topology and CPU feature mask do not prove dedicated physical cores or relative performance against `ali`. The image uses NetworkManager and DHCP on `eth0`, provider DNS, and public IPv4; global IPv6 was not configured when checked. Provider-side filtering, bandwidth, quotas, billing, and storage redundancy have not been verified.

## Configuration Sources

| Source in this skill | Installed location | Behavior |
| --- | --- | --- |
| `assets/vps/00-maintenance.conf` | `/etc/ssh/sshd_config.d/00-maintenance.conf`, 0600 | Public-key authentication; no password or keyboard-interactive authentication; root requires a public key; no X11 forwarding |
| `assets/vps/public.xml` | `/etc/firewalld/zones/public.xml`, 0644 | Public zone allows SSH, proxy TCP 443, ACME HTTP 80, and NAS web HTTPS 8443 |
| `assets/gateway/nginx-main.conf` | `/etc/nginx/nginx.conf` | AlmaLinux include layout for the active gateway; HTTP-01-only bootstrap is no longer the production site |
| `assets/nginx-gateway.conf` and application-owned locations | Distribution's enabled Nginx configuration and `/etc/nginx/app-locations` | Active authenticated web HTTPS 8443, HTTP-01/redirects 80, loopback inspector; no proxy 443 takeover |
| `assets/gateway/30-nas-tunnel.conf` | `/etc/ssh/sshd_config.d/30-nas-tunnel.conf` | Dedicated `nas-tunnel` identity permits only listed loopback reverse forwards, including NAS management 22022; 15-second server heartbeats with three unanswered probes release stale sessions |
| `assets/gateway/certbot-renew.service/timer` | `/etc/systemd/system/certbot-renew.service/timer` | Public IP renewal through isolated `/opt/certbot/.venv` |
| `assets/vps/vps-proxy.service`, `assets/vps/sing-box-config.json.template` | `/etc/systemd/system/vps-proxy.service`, `/etc/vps-proxy/config.json` | Single low-privilege sing-box VLESS + REALITY + Vision service; configuration is privately rendered |
| `assets/vps/automatic.conf` | `/etc/dnf/automatic.conf`, 0644 | Automatically downloads and applies security updates; never reboots automatically; journal output |
| `assets/server-context-motd.txt` | `/etc/motd.d/30-server-context`, 0644 | Static PAM login notice linking to server instructions |
| `assets/AGENTS.md` | `/opt/AGENTS.md`, linked from `/root/AGENTS.md` | Shared server maintenance entry point |

The OpenSSH Include occurs before the image's explicit password and root-login settings. OpenSSH uses the first obtained value, so inspect `sshd -T` after changes rather than reading only the bottom of `sshd_config`. Keep an existing administrative session while validating a fresh key-only connection; do not lock root's account or change its authorized key as part of password-authentication disablement.

Firewalld is enabled at boot, with `public` as the default and the NetworkManager connection on `eth0` assigned to it. Public HTTP 80 and web HTTPS 8443 are active alongside the unchanged proxy TCP 443 listener. Nginx, its public IP certificate, and renewal timer are active; loopback 18080-18087 and management 22022 reach NAS through its dedicated reverse tunnel. Gateway authentication/branding and isolated upload/streaming/Range checks passed, alongside a real installed Hiddify-core proxy HTTPS request. Keep internal listeners private. Essential established traffic, loopback, and ICMP follow firewalld defaults; provider-wide filtering remains outside the verified scope. See [Personal proxy operations](vps-proxy.md) for runtime/client behavior.

The proxy's connection and Hiddify settings are maintained in Yuyan document 833, titled `VPS配置`, reachable through the active Yuyan entrance. Future client/access changes directly revise that document through `yuyan-doc`; ownership, confidentiality, and recovery rules are in [Personal proxy operations](vps-proxy.md#client-configuration-record).

The image boots with `selinux=0 audit=0`; SELinux remains disabled. Enabling it requires a separate policy, relabel, and reboot plan. Guest CPU vulnerability reporting includes MDS mitigation limitations; provider host microcode/isolation cannot be established from the guest alone.

## Updates and Reboot

Use `software-installation` for package changes. AlmaLinux BaseOS, AppStream, and Extras are enabled with RPM signature verification. Use DNF rather than Ubuntu's APT or unattended-upgrades. The initial update advanced AlmaLinux 9.7 to 9.8. Security updates are scheduled by the distribution's `dnf-automatic.timer`; its randomized delay is shown by `systemctl cat dnf-automatic.timer`. Automatic reboot is disabled, so check `needs-restarting -r` and arrange authorized reboots after kernel or core-library updates.

```sh
ssh vps 'cat /opt/AGENTS.md'
ssh vps 'bash /opt/server-context/scripts/inspect.sh'
ssh vps 'dnf check-update; dnf updateinfo summary --security'
ssh vps 'systemctl list-timers dnf-automatic.timer --all --no-pager'
ssh vps 'journalctl -u dnf-automatic.service --no-pager -n 40'
ssh vps 'sshd -T | grep -E "^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication) "'
ssh vps 'firewall-cmd --get-active-zones; firewall-cmd --zone=public --list-all'
```

Before a reboot, finish package transactions, verify `grubby --default-kernel`, confirm the selected kernel and initramfs exist, and validate a new SSH connection. After an authorized reboot, require a changed boot ID and verify running kernel, key-only SSH, firewalld, NetworkManager, chronyd, update timer, DNS/HTTPS, and failed units. Do not count a successful TCP connection as a complete reboot check.

## Context and Recovery

Run `SYNC_HOST=vps ~/agent-config/skills/server-operations/scripts/sync-docs.sh shared` after committing and pushing shared documentation. `--check shared` verifies synchronized file hashes and provenance. Synchronization installs documentation and login notices, not the SSH, firewall, or update configuration assets above. Root's instruction link is created only after confirming there is no existing conflicting `/root/AGENTS.md`.

The user waived an additional retained migration recovery package. Approved historical pre-change archives, staging, and retired Xray binary/configuration/unit were removed; the `xray` user/group remain because live sing-box uses them. Cleanup preserved live proxy/Nginx processes and all current proxy/gateway/certificate/ACME/SSH/tunnel/firewall configuration. The first verified combined NAS/VPS external set now includes private VPS proxy, Nginx, public certificate/ACME, SSH/tunnel, firewall and maintained recovery configuration; [current-state](current-state.md#manual-data-archives) owns its acceptance. Yuyan 833 contains client settings, not the server private key or a recovery set. VPS sends raw recovery material to NAS for the single compression/external-copy workflow in [Agent backup and recovery](backup-recovery.md). Record coverage only after actual capture/verification; do not recreate a maintained `~/vps` directory or schedule backups.

VPS hosts no application databases or application runtime instances. Its primary public Web HTTPS 8443 entrance reaches the same NAS state as the LAN and compatibility ALI entrances. Yuyan agent operations and VPS SSH maintenance default to the `vps` alias; AICalendar imports default to direct NAS LAN HTTPS and stop on LAN connection failure without public fallback. [Current-state](current-state.md) defines the explicit VPS upload opt-in. Existing ALI web access remains usable independently of that import policy. Physical device logins on the new Origin remain separate from historical CLI acceptance. For rebuild, use AlmaLinux dependencies and the VPS host namespace selected from the combined recovery package; do not restore NAS identities/configuration onto VPS.

For SSH lockout, use the provider console and inspect or remove the maintenance drop-in, then run `sshd -t` before reloading. For a firewall lockout, inspect the NetworkManager zone and public-zone services through the console; restore only the required SSH access. A previous installed kernel remains available through GRUB after the initial update; kernel rollback does not roll back userspace packages. DNF history and any separately retained configuration archive provide distinct evidence or recovery options, not a guaranteed whole-system restore.
