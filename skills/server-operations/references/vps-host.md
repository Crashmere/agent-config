# VPS Operations

`vps` is a separate AlmaLinux KVM VM. It does not host the applications on `ali` and has no connection to the storage or power policy of `nas`. Resolve its address and administrator key from local OpenSSH configuration; do not put them in this public repository.

## Host and Access

The local alias is `ssh vps`, with root public-key authentication, port 22, explicit identity selection, strict host-key verification, and 30-second keepalives. The hostname is `vps`; time is Asia/Shanghai with chrony synchronization. The guest has 2 vCPU, about 1 GiB RAM, 544 MiB swap, and a 20 GiB virtual disk divided into ext4 `/boot` and `/`. Kernel and package versions are volatile; query them rather than pinning the initial image version.

The VM advertises an Intel Xeon SierraForest CPU model. Its virtual topology and CPU feature mask do not prove dedicated physical cores or relative performance against `ali`. The image uses NetworkManager and DHCP on `eth0`, provider DNS, and public IPv4; global IPv6 was not configured when checked. Provider-side filtering, bandwidth, quotas, billing, and storage redundancy have not been verified.

## Configuration Sources

| Source in this skill | Installed location | Behavior |
| --- | --- | --- |
| `assets/vps/00-maintenance.conf` | `/etc/ssh/sshd_config.d/00-maintenance.conf`, 0600 | Public-key authentication; no password or keyboard-interactive authentication; root requires a public key; no X11 forwarding |
| `assets/vps/public.xml` | `/etc/firewalld/zones/public.xml`, 0644 | Public zone allows SSH only; no public application ports |
| `assets/vps/automatic.conf` | `/etc/dnf/automatic.conf`, 0644 | Automatically downloads and applies security updates; never reboots automatically; journal output |
| `assets/server-context-motd.txt` | `/etc/motd.d/30-server-context`, 0644 | Static PAM login notice linking to server instructions |
| `assets/AGENTS.md` | `/opt/AGENTS.md`, linked from `/root/AGENTS.md` | Shared server maintenance entry point |

The OpenSSH Include occurs before the image's explicit password and root-login settings. OpenSSH uses the first obtained value, so inspect `sshd -T` after changes rather than reading only the bottom of `sshd_config`. Keep an existing administrative session while validating a fresh key-only connection; do not lock root's account or change its authorized key as part of password-authentication disablement.

Firewalld is enabled at boot, with `public` as the default and the NetworkManager connection on `eth0` assigned to it. Essential established traffic, loopback, and ICMP follow firewalld defaults. Inspect active zones, services, and the nftables ruleset before changing exposure. Opening HTTP/HTTPS or other public ports requires authorization; copying `ali`'s inactive UFW state is not a host requirement.

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

Private pre-change configuration is retained in root-only `/root/maintenance-backups/` with 0600 archives; these include SSH configuration and must never enter Git or shared context. They are local configuration recovery materials, not application or off-host backups. There are no business data, application runtimes, VPN, public HTTPS service, or scheduled application backups on `vps`. Production remains on `ali`.

For SSH lockout, use the provider console and inspect or remove the maintenance drop-in, then run `sshd -t` before reloading. For a firewall lockout, inspect the NetworkManager zone and public-zone services through the console; restore only the required SSH access. A previous installed kernel remains available through GRUB after the initial update; kernel rollback does not roll back userspace packages. DNF history and private configuration archives provide separate evidence and recovery options, not a guaranteed whole-system restore.
