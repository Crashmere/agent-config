# NAS Laptop Operations

SSH alias `nas` identifies the ASUS G733 laptop, hostname `striker`. It is a separately prepared host; all business applications remain on `ali`. Use the shared authorization table before changes. Read `/opt/AGENTS.md` explicitly on every new remote maintenance task.

## Hardware and access

- Ubuntu 26.04.1 LTS / amd64; Ryzen 9 5900HX, 8 cores and 16 threads; 64 GB installed RAM.
- Intel SSDPEKKF010T8L, 1 TB: EFI partition and ext4 `/`; 8 GB swapfile. Identify disks by model and filesystem UUID because NVMe device numbering can change.
- Samsung MZVLB1T0HBLR, 1 TB: GPT with one ext4 data partition, label `nas-data`, mounted at `/data`. The user authorized removal of the former BitLocker partition on 2026-10-28. Ordinary user `nas` can write in private `/data/nas`; application data belongs in separately assigned directories and identities.
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

The battery reported about 62 Wh full-charge capacity versus 90 Wh design capacity during preparation. A charge limit does not forcibly discharge a battery already above that limit. Keep vents clear when running with the lid closed. Physical lid closure was verified through logind's `LidClosed=true` and a successful SSH connection; the host remained running and the NVIDIA GPU was suspended. Full power-loss recovery and boot-time persistence still require an actual restart before unattended production use.

To remove the power policy, disable `nas-power.service` and remove the logind drop-in, then reload logind. Restore the previous `balanced` firmware profile, `balance_performance` CPU preference, and 100% charge threshold when appropriate. Network rollback removes only the added Ethernet overlay and regenerates Netplan; preserve the installer Wi-Fi configuration.

## Tools and storage checks

The Samsung data filesystem uses 1% reserved blocks. Mount configuration comes from `assets/nas/data.fstab`, with `__NAS_DATA_UUID__` replaced by the actual ext4 UUID in `/etc/fstab`. Obtain it from `blkid` after matching the disk model; never rely on a fixed NVMe device number. `noatime` avoids access-time writes. `nofail` and a ten-second device timeout let `nas` boot for remote recovery when the data disk is absent. Future services that store data there must use `RequiresMountsFor=/data` so they fail instead of writing into the unmounted directory on the Intel system disk.

After a mount-configuration change, run `findmnt --verify` and `systemctl daemon-reload`, then start `data.mount` and verify its Result. The initial configuration passed a stop/start of `data.mount` and ordinary-user write/read/hard-link checks. It provided approximately 929 GiB available after formatting. Full reboot validation remains pending. Original partition metadata and fstab were saved in root-private `/root/nas-storage-before-*`; these metadata copies cannot recover the formatted BitLocker content.

The Intel and Samsung filesystems are separate. Keep an application's media and hard-link backup directories on the same filesystem. `/data` is active storage, not an independent backup of the Intel SSD; off-host copies need a separate backup arrangement.

Installed from Ubuntu repositories: ripgrep, smartmontools, nvme-cli, libvips-tools, libheif-plugin-libde265, ExifTool, and FFmpeg. The existing curl, ca-certificates, rsync, and Python 3 remain available. smartmontools monitoring and weekly `fstrim.timer` are enabled. Application builds remain on the maintenance computer.

Both NVMe drives passed their SMART self-assessment and reported zero media/data-integrity errors during preparation. The Samsung controller's latest error-log entry was `Invalid Field in Command`, with no data namespace/LBA; its nonzero historical error counter alone does not establish media failure. Use SMART and the decoded error log together when diagnosing disk health. No extended self-test was performed.

```sh
ssh nas 'cat /opt/AGENTS.md'
ssh nas 'systemctl --failed; systemctl is-system-running'
ssh nas 'systemctl show nas-power.service systemd-networkd-wait-online.service -p Id -p Result'
ssh nas 'cat /sys/class/power_supply/BAT0/charge_control_end_threshold; cat /sys/firmware/acpi/platform_profile'
ssh nas 'cat /sys/bus/pci/devices/0000:01:00.0/power/runtime_status'
ssh nas 'lsblk -o NAME,MODEL,SIZE,FSTYPE,MOUNTPOINTS; timedatectl'
ssh nas 'findmnt /data; df -hT /data; systemctl show data.mount -p Result'
```

Shared docs synchronize with `SYNC_HOST=nas skills/server-operations/scripts/sync-docs.sh shared` from the pushed agent-config checkout. This creates `/opt/server-context`, `/opt/AGENTS.md`, and the login notice. `/root/AGENTS.md` links to `/opt/AGENTS.md`. The separate `ali` copy must receive shared inventory changes through the same script with its default host.

Application migration, stable router address reservation, public exposure/VPN, and off-host backups are subsequent work. Preserve existing applications and backups on `ali` until their migration and recovery points are separately accepted.
