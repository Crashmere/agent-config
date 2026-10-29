# VPS Operations

`vps` is a separate AlmaLinux KVM VM. Its migration role is public web HTTPS 8443 forwarding to NAS, alongside the existing sing-box proxy on TCP 443; applications and authoritative data belong to NAS. [Current-state](current-state.md) records activation, and [NAS migration](nas-migration.md) owns shared access/recovery. Resolve its address and administrator key from trusted local SSH configuration; do not put them in this public repository.

## Host and Access

The local alias is `ssh vps`, with root public-key authentication, port 22, explicit identity selection, strict host-key verification, and 30-second keepalives. The hostname is `vps`; time is Asia/Shanghai with chrony synchronization. The guest has 2 vCPU, about 1 GiB RAM, 544 MiB swap, and a 20 GiB virtual disk divided into ext4 `/boot` and `/`. Kernel and package versions are volatile; query them rather than pinning the initial image version.

The VM advertises an Intel Xeon SierraForest CPU model. Its virtual topology and CPU feature mask do not prove dedicated physical cores or relative performance against `ali`. The image uses NetworkManager and DHCP on `eth0`, provider DNS, and public IPv4; global IPv6 was not configured when checked. Provider-side filtering, bandwidth, quotas, billing, and storage redundancy have not been verified.

## Configuration Sources

| Source in this skill | Installed location | Behavior |
| --- | --- | --- |
| `assets/vps/00-maintenance.conf` | `/etc/ssh/sshd_config.d/00-maintenance.conf`, 0600 | Public-key authentication; no password or keyboard-interactive authentication; root requires a public key; no X11 forwarding |
| `assets/vps/public.xml` | `/etc/firewalld/zones/public.xml`, 0644 | Public zone allows SSH, proxy TCP 443, ACME HTTP 80, and NAS web HTTPS 8443 |
| `assets/gateway/nginx-main.conf`, `nginx-bootstrap.conf` | `/etc/nginx/nginx.conf` and a temporary enabled server | AlmaLinux Nginx include layout; public HTTP-01 only while the certificate/authenticated site is being prepared |
| `assets/nginx-gateway.conf` | Distribution's enabled Nginx configuration | VPS web HTTPS 8443, HTTP-01/redirects 80, loopback inspector; no proxy 443 takeover |
| `assets/gateway/30-nas-tunnel.conf` | `/etc/ssh/sshd_config.d/30-nas-tunnel.conf` | Dedicated `nas-tunnel` identity permits only listed loopback reverse forwards, including NAS management 22022 |
| `assets/gateway/certbot-renew.service/timer` | `/etc/systemd/system/certbot-renew.service/timer` | Public IP renewal through isolated `/opt/certbot/.venv` |
| `assets/vps/vps-proxy.service`, `assets/vps/sing-box-config.json.template` | `/etc/systemd/system/vps-proxy.service`, `/etc/vps-proxy/config.json` | Single low-privilege sing-box VLESS + REALITY + Vision service; configuration is privately rendered |
| `assets/vps/automatic.conf` | `/etc/dnf/automatic.conf`, 0644 | Automatically downloads and applies security updates; never reboots automatically; journal output |
| `assets/server-context-motd.txt` | `/etc/motd.d/30-server-context`, 0644 | Static PAM login notice linking to server instructions |
| `assets/AGENTS.md` | `/opt/AGENTS.md`, linked from `/root/AGENTS.md` | Shared server maintenance entry point |

The OpenSSH Include occurs before the image's explicit password and root-login settings. OpenSSH uses the first obtained value, so inspect `sshd -T` after changes rather than reading only the bottom of `sshd_config`. Keep an existing administrative session while validating a fresh key-only connection; do not lock root's account or change its authorized key as part of password-authentication disablement.

Firewalld is enabled at boot, with `public` as the default and the NetworkManager connection on `eth0` assigned to it. Proxy TCP 443 remains unchanged. The approved gateway migration adds only public HTTP 80 and web HTTPS 8443; keep application ports and NAS management 22022 on loopback. Essential established traffic, loopback, and ICMP follow firewalld defaults. Inspect actual rules and provider-side filtering before activation; do not copy ALI's inactive UFW state or replace a zone in ways that remove the proxy. See [Personal proxy operations](vps-proxy.md) for runtime/client behavior.

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

Private pre-change configuration remains in root-only `/root/maintenance-backups/` with 0600 archives. Proxy recovery currently has no independent copy after the user-requested removal of local `~/vps`; Yuyan 833 lacks the server private key. The manual gateway recovery package must capture the current proxy together with Nginx, public certificate/ACME, SSH/tunnel, firewall, and maintained configuration. Record that independent coverage only after actual capture/verification; do not recreate a maintained `~/vps` directory or schedule backups.

VPS hosts no application databases or application runtime instances. Shared current-state determines whether web 8443 has been activated; source templates alone do not establish live service. For rebuild, use AlmaLinux dependencies and verified gateway/proxy materials, keeping NAS data in its own recovery set.

For SSH lockout, use the provider console and inspect or remove the maintenance drop-in, then run `sshd -t` before reloading. For a firewall lockout, inspect the NetworkManager zone and public-zone services through the console; restore only the required SSH access. A previous installed kernel remains available through GRUB after the initial update; kernel rollback does not roll back userspace packages. DNF history and private configuration archives provide separate evidence and recovery options, not a guaranteed whole-system restore.
