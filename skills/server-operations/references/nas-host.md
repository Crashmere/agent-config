# NAS Laptop Operations

SSH alias `nas` identifies the ASUS G733 laptop, hostname `striker`. It is a separately prepared host; all business applications remain on `ali`. Use the shared authorization table before changes. Read `/opt/AGENTS.md` explicitly on every new remote maintenance task.

## Hardware and access

- Ubuntu 26.04.1 LTS / amd64; Ryzen 9 5900HX, 8 cores and 16 threads; 64 GB installed RAM.
- Intel SSDPEKKF010T8L, 1 TB: approximately 1 GiB EFI System Partition at `/boot/efi`; the remaining partition is an LVM physical volume in `nasvg`.
- Samsung MZVLB1T0HBLR, 1 TB: GPT with 2 GiB ext4 `/boot` and an LVM physical volume in `nasvg`. The user authorized replacing the former BitLocker content and then combining both SSDs on 2026-10-28.
- The linear logical volume `nasvg/root` spans both SSDs and holds a single ext4 `/`, approximately 1.86 TiB before filesystem overhead. `/opt`, `/home`, and `/data` share this capacity. `/data/nas` is private to ordinary user `nas`. The 8 GiB swapfile remains `/swap.img`. Identify devices by model, serial, and UUID; their NVMe numbering changed during restart verification.
- NVIDIA RTX 3070 uses the kernel nouveau driver; the internal display uses amdgpu. No proprietary graphics driver was added during preparation.
- Local `ssh nas` uses root and `~/.ssh/ubuntu_nas_ed25519`. Ordinary-user access remains available as `ssh -l nas nas`. Root accepts keys only (`PermitRootLogin prohibit-password`); ordinary-user password authentication remains enabled. Host fingerprints are verified through the local console and retained in the maintenance computer's known_hosts.
- SSH uses enabled `ssh.socket`, listening on port 22. No application HTTP/HTTPS listener, VPN, or host firewall policy was added during preparation.

## Network and time

Wi-Fi `wlp3s0` uses DHCP through systemd-networkd. Credentials reside only in root-private `/etc/netplan/00-installer-config.yaml`. Keep that file out of Git and redact credentials before inspection. A router DHCP reservation is still needed for a stable maintenance address; obtain the current address from local SSH configuration and Wi-Fi MAC from `ip link show wlp3s0`.

Ethernet `enp2s0` uses DHCP with route metric 100 and is optional during boot. The source is `assets/nas/ethernet.yaml`, installed mode 0600 at `/etc/netplan/80-nas-ethernet.yaml`. Wi-Fi remains configured when a cable is connected. See [the wait-online fix](common-issues.md#network-startup-waits-for-an-unplugged-interface) before adjusting network startup.

Timezone is Asia/Shanghai. The existing chrony service provides time synchronization. Ubuntu's signed `cn.archive.ubuntu.com` and `security.ubuntu.com` repositories provide updates; apt-daily and apt-daily-upgrade timers are enabled. Automatic reboot is not enabled. Package installation output from initial preparation is local at `/var/log/nas-preparation-packages.log`.

## Laptop power

| Source | Installed configuration | Behavior |
| --- | --- | --- |
| `assets/nas/logind.conf` | `/etc/systemd/logind.conf.d/80-nas-server.conf` | Lid, suspend key, and hibernate key do not suspend the host; idle action is ignored |
| `assets/nas/apply-power.sh` and `power.service` | `/opt/server-context/assets/nas/apply-power.sh` and `/etc/systemd/system/nas-power.service` | At boot, apply 80% charge limit, firmware `quiet` profile, CPU `balance_power`, and keyboard backlight off |

The power unit is enabled at multi-user startup. After source synchronization, install the configuration files, run `systemctl daemon-reload`, then restart `nas-power.service`. Reload logind settings with `systemctl kill --kill-whom=main --signal=HUP systemd-logind.service`; restarting logind is unnecessary.

NVIDIA runtime power management is already automatic. During preparation it reached `runtime_status=suspended` after idle time. Hardware probes can wake it temporarily; inspect its sysfs runtime status without repeatedly running GPU enumeration tools. No GPU removal, driver blacklisting, or manual PCI unbinding is configured. On 2026-10-28, the user measured approximately 11 W average wall power with a power meter in the prepared, closed-lid state. The measurement duration was not provided; this result does not establish power consumption under media-processing load.

The battery reported about 62 Wh full-charge capacity versus 90 Wh design capacity during preparation. A charge limit does not forcibly discharge a battery already above that limit. Keep vents clear when running with the lid closed. Physical lid closure was verified through logind's `LidClosed=true` and a successful SSH connection; the host remained running and the NVIDIA GPU was suspended. Charging and firmware preferences persisted through the storage-migration restarts. Automatic startup after a complete power loss remains unverified.

To remove the power policy, disable `nas-power.service` and remove the logind drop-in, then reload logind. Restore the previous `balanced` firmware profile, `balance_performance` CPU preference, and 100% charge threshold when appropriate. Network rollback removes only the added Ethernet overlay and regenerates Netplan; preserve the installer Wi-Fi configuration.

## Tools and storage checks

The unified ext4 root uses 1% reserved blocks and `noatime`. Mount configuration comes from `assets/nas/root.fstab`, rendered with actual root, boot, and EFI UUIDs. `/data` has no separate mount or `data.mount` unit. Files in application data and native hard-link backup directories can share the root filesystem. Same-host copies remain vulnerable to loss of the host or storage pool.

Boot files remain outside LVM. Secure Boot loads the existing signed Ubuntu shim/GRUB from the Intel EFI partition; `EFI/ubuntu/grub.cfg` locates Samsung's `/boot` by UUID and uses `/grub` as its prefix. GRUB loads the kernel and LVM-enabled initramfs, which activates `nasvg/root`. `assets/nas/grub-storage.cfg`, installed at `/etc/default/grub.d/90-nas-storage.cfg`, exposes a five-second menu and disables os-prober. For kernel or storage changes, regenerate initramfs and GRUB configuration with `/boot` and `/boot/efi` mounted.

Before replacing the old Intel root, an approximately 2.3 GiB independent root archive was saved to the maintenance Mac under `~/ali/backups/nas-lvm-*`, outside Git. Its checksum matched the archive on `nas` and gzip validation passed. It preserves software, private host configuration, old `/boot`, and an EFI copy; runtime mounts and the swapfile are excluded. The adjacent README describes recovery. Preserve this backup; original partition metadata alone cannot recover formatted content.

The user accepted the linear layout's failure behavior: neither SSD is a mirror, and failure of either can make the entire root filesystem unavailable. Future capacity expansion uses a verified additional physical volume, `vgextend`, `lvextend`, and filesystem resizing; it requires an independent backup and appropriate change authorization. For recovery, boot a local Ubuntu USB, inspect both SSDs and LVM metadata, then repair or restore to separately identified storage. Do not format a missing/failed root to conceal data loss.

The conversion passed a one-shot LVM boot, a reboot through the new EFI default, and a final reboot after adding the Intel physical volume. Secure Boot remained enabled. `/`, `/opt`, and `/data` reported the same filesystem device; a hard link from `/opt` to `/data` and ordinary-user read/write checks passed. The completed filesystem reported approximately 2.01 TB total and 1.99 TB available in decimal units. SSH, Wi-Fi, the charge limit, firmware profile, and wait-online unit recovered after the final restart; no failed services remained.

During migration, `nas` became unresponsive while an SSH-streamed archive was transferring; the local console also stopped responding. After a user-assisted restart, the previous journal contained no conclusive panic, OOM, disk timeout, or media-error evidence. Samsung's staged filesystem replayed its journal cleanly. A locally generated archive with bounded resources and a resumable 8 MiB/s transfer subsequently completed. The cause of the single freeze remains unresolved. A CPU temperature near 90 degrees Celsius was observed during archive work, without proof of causation; firmware `balanced` and disabled CPU boost were used temporarily during migration to lower temperature.

Installed from Ubuntu repositories: ripgrep, smartmontools, nvme-cli, libvips-tools, libheif-plugin-libde265, ExifTool, and FFmpeg. The existing curl, ca-certificates, rsync, and Python 3 remain available. smartmontools monitoring and weekly `fstrim.timer` are enabled. Application builds remain on the maintenance computer.

Both NVMe drives passed their SMART self-assessment and reported zero media/data-integrity errors during preparation. The Samsung controller's latest error-log entry was `Invalid Field in Command`, with no data namespace/LBA; its nonzero historical error counter alone does not establish media failure. Use SMART and the decoded error log together when diagnosing disk health. No extended self-test was performed.

```sh
ssh nas 'cat /opt/AGENTS.md'
ssh nas 'systemctl --failed; systemctl is-system-running'
ssh nas 'systemctl show nas-power.service systemd-networkd-wait-online.service -p Id -p Result'
ssh nas 'cat /sys/class/power_supply/BAT0/charge_control_end_threshold; cat /sys/firmware/acpi/platform_profile'
ssh nas 'cat /sys/bus/pci/devices/0000:01:00.0/power/runtime_status'
ssh nas 'lsblk -o NAME,MODEL,SIZE,FSTYPE,MOUNTPOINTS; timedatectl'
ssh nas 'findmnt /; findmnt /boot; findmnt /boot/efi; df -hT /'
ssh nas 'pvs; vgs; lvs --segments -o lv_name,vg_name,lv_size,segtype,devices'
```

Shared docs synchronize with `SYNC_HOST=nas skills/server-operations/scripts/sync-docs.sh shared` from the pushed agent-config checkout. This creates `/opt/server-context`, `/opt/AGENTS.md`, and the login notice. `/root/AGENTS.md` links to `/opt/AGENTS.md`. The separate `ali` copy must receive shared inventory changes through the same script with its default host.

Application migration, stable router address reservation, public exposure/VPN, and off-host backups are subsequent work. Preserve existing applications and backups on `ali` until their migration and recovery points are separately accepted.
