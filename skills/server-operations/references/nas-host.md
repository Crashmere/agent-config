# NAS Laptop Operations

SSH alias `nas` identifies the ASUS G733 laptop, hostname `striker`. It hosts all eight active application instances and authoritative data after the accepted 2026-10-30 cutover; [current-state](current-state.md) records acceptance and remaining physical/recovery scope. [NAS migration](nas-migration.md) owns ALI/VPS forwarding, authentication, manual external backup, and recovery. Use the shared authorization table before changes and explicitly read `/opt/AGENTS.md` on every new remote maintenance task.

## Hardware and access

- Ubuntu 26.04.1 LTS / amd64; Ryzen 9 5900HX, 8 cores and 16 threads; 64 GB installed RAM.
- Intel SSDPEKKF010T8L, 1 TB: approximately 1 GiB EFI System Partition at `/boot/efi`; the remaining partition is an LVM physical volume in `nasvg`.
- Samsung MZVLB1T0HBLR, 1 TB: GPT with 2 GiB ext4 `/boot` and an LVM physical volume in `nasvg`. The user authorized replacing the former BitLocker content and then combining both SSDs on 2026-10-28.
- The linear logical volume `nasvg/root` spans both SSDs and holds a single ext4 `/`, approximately 1.86 TiB before filesystem overhead. `/opt`, `/home`, and `/data` share this capacity. `/data/nas` is private to ordinary user `nas`. The 8 GiB swapfile remains `/swap.img`. Identify devices by model, serial, and UUID; their NVMe numbering changed during restart verification.
- NVIDIA RTX 3070 uses the kernel nouveau driver; the internal display uses amdgpu. No proprietary graphics driver was added during preparation.
- Local `ssh nas` uses root and `~/.ssh/ubuntu_nas_ed25519`. Ordinary-user access remains available as `ssh -l nas nas`. Root accepts keys only (`PermitRootLogin prohibit-password`); ordinary-user password authentication remains enabled. Host fingerprints are verified through the local console and retained in the maintenance computer's known_hosts.
- SSH uses enabled `ssh.socket`, listening on port 22. The trusted `nas-via-vps` maintenance alias reaches the same NAS SSH service through VPS loopback 22022, retaining the previously verified NAS host key; it supplements rather than replaces the LAN alias. Application listeners and gateway activation are recorded in [current-state](current-state.md); no new host VPN or firewall policy is part of this migration.

## Network and time

Wi-Fi `wlp3s0` uses DHCP through systemd-networkd. Credentials reside only in root-private `/etc/netplan/00-installer-config.yaml`. Keep that file out of Git and redact credentials before inspection. The user deferred a router reservation and retained the current DHCP address for migration. Obtain it from trusted local SSH configuration; a changed address requires coordinated maintenance settings, local-CA SAN, Origins, and shortcut updates rather than assuming fixed reachability.

Ethernet `enp2s0` uses DHCP with route metric 100 and is optional during boot. The source is `assets/nas/ethernet.yaml`, installed mode 0600 at `/etc/netplan/80-nas-ethernet.yaml`. Wi-Fi remains configured when a cable is connected. See [the wait-online fix](common-issues.md#network-startup-waits-for-an-unplugged-interface) before adjusting network startup.

Timezone is Asia/Shanghai. The existing chrony service provides time synchronization. Ubuntu's signed `cn.archive.ubuntu.com` and `security.ubuntu.com` repositories provide updates; apt-daily and apt-daily-upgrade timers are enabled. Automatic reboot is not enabled. Package installation output from initial preparation is local at `/var/log/nas-preparation-packages.log`.

## Application and Gateway Role

All eight application units, Portal's local root collector, and Nginx are active and enabled. `assets/nginx-nas.conf` provides authenticated LAN HTTPS 443 and loopback inspection; ALI/VPS public entrances forward to the same NAS services. The active `nas-lan-tls.timer` invokes `nas-lan-tls.service` and `assets/nas/renew-lan-tls.sh` to maintain the CA-signed leaf under `/etc/nas-ca`; the renewal oneshot passed verification. Devices import only the public CA root, available through Portal's trusted VPS `/portal/connect` setup page; private signing and tunnel keys remain on NAS. [Portal maintenance](portal.md#public-nas-device-setup) owns the four-platform setup contract. CLI TLS checks passed. On 2026-10-30, the user confirmed completing NAS local-CA onboarding through Portal in the maintenance Mac's browser; Aura native-client trust, other NAS browser/app/platform flows, and VPS Portal device logins remain unverified.

Both `reverse-tunnel@ali.service` and `reverse-tunnel@vps.service` are active and enabled. They use the dedicated `nas-tunnel` identity and root-managed `/etc/nas-tunnels`; gateway listeners remain loopback-only. `/etc/server-maintenance-host` contains `nas`, `/run/lock/server-maintenance.lock` coordinates upgrades/full backups, and root-private `/var/lib/server-upgrades` is reserved for temporary upgrade protection. Initial migration used isolated check candidates, not extra upgrade snapshots. The accepted candidates, migration staging/private copies, bulky verification baselines, and Ledger's historical `before-schema2` snapshot were removed without changing live service processes; small per-release migration receipts remain.

The installed `/etc/tmpfiles.d/server-maintenance.conf`, sourced from `assets/nas/server-maintenance.tmpfiles.conf`, creates the global and FabricWorld/RecipeBox deployment locks as root-owned 0644 files so cleanup can acquire read-only descriptors. `fabricworld-cleanup.timer` and `recipebox-cleanup.timer` are active and enabled for native expired-record/media cleanup under these locks. They create no snapshots or backup-pruning work; the seven legacy native backup timers and backup/release-pruning schedules remain disabled.

The known Samsung T7 exFAT data partition (UUID `BCDD-941E`) passed its first real full NAS/VPS external-backup acceptance on 2026-10-31 and was safely unmounted afterward; [current-state](current-state.md#manual-data-archives) records the coverage and verification boundary. Its existing user files are protected. Manual dual-host backups temporarily stage NAS/VPS material and one compressed package under root-private `/var/lib/server-backups`, copying and verifying externally before successful task cleanup; no retained routine internal backup/cache is kept and missing media never redirects to root storage. The earlier failed stage remains for investigation. Live application data and derivatives are unaffected. The frozen ALI migration-point fallback and protected pre-existing Mac backups remain untouched. [Agent backup and recovery](backup-recovery.md) owns `/etc/server-recovery.json` and `/opt/server-recovery` and [retention](retention.md) owns successful temporary-protection deletion.

## Laptop Power

| Source | Installed configuration | Behavior |
| --- | --- | --- |
| `assets/nas/logind.conf` | `/etc/systemd/logind.conf.d/80-nas-server.conf` | Lid, suspend key, and hibernate key do not suspend the host; idle action is ignored |
| `assets/nas/apply-power.sh` and `power.service` | `/opt/server-context/assets/nas/apply-power.sh` and `/etc/systemd/system/nas-power.service` | Apply 80% charge limit, firmware `balanced`, CPU `balance_power`, boost disabled, C2/C3 requests disabled on every CPU, and keyboard backlight off |
| `assets/nas/grub-stability.cfg` | `/etc/default/grub.d/95-nas-stability.cfg` | Append `processor.max_cstate=1` so the `acpi_idle` driver excludes deeper states before userspace starts |

The power unit is enabled at multi-user startup. After source synchronization, install the configuration files, run `systemctl daemon-reload`, then restart `nas-power.service`. Reload logind settings with `systemctl kill --kill-whom=main --signal=HUP systemd-logind.service`; restarting logind is unnecessary.

NVIDIA runtime power management is automatic. During preparation it reached `runtime_status=suspended` after idle time. Hardware probes can wake it temporarily; inspect its sysfs runtime status without repeatedly running GPU enumeration tools. No GPU removal, driver blacklisting, or manual PCI unbinding is configured. On 2026-10-28, the user measured approximately 11 W average wall power with a power meter under the earlier `quiet` policy with boost enabled and unrestricted CPU idle states, then reported approximately 14 W while idle after the diagnostic reboot. Measurement durations and comparable display/lid conditions were not recorded, so the readings do not establish a controlled power difference or media-processing consumption. The diagnostic C1 limit can increase idle power, and disabled boost reduces peak throughput.

The battery reported about 62 Wh full-charge capacity versus 90 Wh design capacity during preparation. A charge limit does not forcibly discharge a battery already above that limit. Keep vents clear when running with the lid closed. Physical lid closure was verified through logind's `LidClosed=true` and a successful SSH connection; the host remained running and the NVIDIA GPU was suspended. Charging and firmware preferences persisted through the storage-migration restarts. Automatic startup after a complete power loss remains unverified.

To roll back the diagnostic power changes, restore the earlier `quiet` profile, enable boost, and remove `/etc/default/grub.d/95-nas-stability.cfg`, then run `update-grub` with both boot mounts present. Restore the matching `apply-power.sh` source so the unit does not reapply the diagnostic controls. For a host started without the kernel C1 limit, write `0` to each C2/C3 `disable` file to restore those states immediately. Once the host has booted with `processor.max_cstate=1`, a separately authorized restart without that parameter is required to expose deeper states again. Keep the charge limit, lid policy, and network settings independent of this diagnostic rollback. Removing the entire preparation policy additionally disables `nas-power.service`, removes the logind drop-in and reloads logind, and restores charging/energy preferences as needed. Network rollback removes only the added Ethernet overlay and regenerates Netplan; preserve the installer Wi-Fi configuration.

## Tools and storage checks

The unified ext4 root uses 1% reserved blocks and `noatime`. Mount configuration comes from `assets/nas/root.fstab`, rendered with actual root, boot, and EFI UUIDs. `/data` has no separate mount or `data.mount` unit. Application data/derivatives and temporary upgrade protection share the root filesystem; same-host copies remain vulnerable to loss of either SSD or the host.

Boot files remain outside LVM. Secure Boot loads the existing signed Ubuntu shim/GRUB from the Intel EFI partition; `EFI/ubuntu/grub.cfg` locates Samsung's `/boot` by UUID and uses `/grub` as its prefix. GRUB loads the kernel and LVM-enabled initramfs, which activates `nasvg/root`. `assets/nas/grub-storage.cfg`, installed at `/etc/default/grub.d/90-nas-storage.cfg`, exposes a five-second menu and disables os-prober. For kernel or storage changes, regenerate initramfs and GRUB configuration with `/boot` and `/boot/efi` mounted.

Before replacing the old Intel root, an approximately 2.3 GiB independent root archive was saved to the maintenance Mac under `~/ali/backups/nas-lvm-*`, outside Git. Its checksum matched the archive on `nas` and gzip validation passed. It preserves software, private host configuration, old `/boot`, and an EFI copy; runtime mounts and the swapfile are excluded. The adjacent README describes recovery. Preserve this backup; original partition metadata alone cannot recover formatted content.

The user accepted the linear layout's failure behavior: neither SSD is a mirror, and failure of either can make the entire root filesystem unavailable. Future capacity expansion uses a verified additional physical volume, `vgextend`, `lvextend`, and filesystem resizing; it requires an independent backup and appropriate change authorization. For recovery, boot a local Ubuntu USB, inspect both SSDs and LVM metadata, then repair or restore to separately identified storage. Do not format a missing/failed root to conceal data loss.

The conversion passed a one-shot LVM boot, a reboot through the new EFI default, and a final reboot after adding the Intel physical volume. Secure Boot remained enabled. `/`, `/opt`, and `/data` reported the same filesystem device; a hard link from `/opt` to `/data` and ordinary-user read/write checks passed. The completed filesystem reported approximately 2.01 TB total and 1.99 TB available in decimal units. SSH, Wi-Fi, the charge limit, firmware profile, and wait-online unit recovered after the final restart; no failed services remained.

For recurring freezes and the diagnostic power policy, see [Freeze diagnostics](#freeze-diagnostics). The successful storage-migration boots verify the boot and filesystem layout; they do not establish long-term hardware stability.

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

## Freeze diagnostics

On 2026-10-28, the user reported that `nas` froze after being left overnight and again after a restart/login, and that the same laptop had also frozen under Windows. During the earlier storage migration, the local console and network became unresponsive during archive transfer. No conclusive panic, OOM, disk timeout, or media-error evidence was retained. A CPU temperature near 90 degrees Celsius was observed during compression, without evidence that temperature caused that freeze.

The overnight boot's retained journal and sysstat data end at 02:40:05. CPU idle time in the last several ten-minute samples was approximately 99.9%, with zero I/O wait; this does not identify the precise freeze time. The subsequent failed boot's persisted journal ends during early userspace initialization, so it does not establish a password/authentication cause. Both drives again reported zero media/data-integrity errors. The machine has two matching Samsung 32 GB DDR4-3200 modules, no ECC, and BIOS G733QR.331. Windows recurrence requires investigating hardware/firmware alongside Linux drivers; absence of logged errors does not exclude memory, power, or controller faults.

A later external-backup attempt exposed a single-bit difference in a private cold-copy database while the production file still matched its captured hash. Read-only comparison, independent checksum paths and a bounded 4 GiB memory check narrowed the symptom without identifying its cause. Preserve the failed material and follow [cold-staging integrity diagnosis](common-issues.md#cold-staging-fails-later-content-verification); the passing short tests do not clear the host's complete memory or copy/write-back path.

The current diagnostic policy removes deep CPU idle requests and boost and restores the firmware's balanced fan policy. It is a reversible mitigation under evaluation, not an established root-cause fix. `acpi_idle` was verified as the active driver before choosing `processor.max_cstate=1`; do not copy Intel-only parameters or use `idle=poll` as a permanent low-power policy. The power script applies the equivalent sysfs restriction on the running host. After installing the overlay and regenerating GRUB, a user-authorized reboot verified `max_cstate=1`, with only POLL/C1 exposed, `balanced`, boost disabled, and the 80% charge limit. SSH for root and ordinary user `nas`, Wi-Fi, the LVM root and separate boot mounts, Secure Boot, the collector timer, and kdump recovered; no failed services or matching hardware/storage/lockup errors were recorded. The user also confirmed local password login and subsequent command input worked. A later home check recorded roughly 35 hours of uninterrupted idle runtime and minute sampling under this policy. This does not identify the earlier freeze cause or prove loaded-service stability; the user has deferred further investigation. NVIDIA, NVMe APST, PCIe ASPM, Wi-Fi, and the LVM layout retain their existing settings so later changes can be evaluated separately.

| Source | Installed configuration | Purpose |
| --- | --- | --- |
| `assets/nas/journald.conf` | `/etc/systemd/journald.conf.d/80-nas-diagnostics.conf` | Persistent journal, 15-second synchronization, 512 MiB journal cap |
| `assets/nas/sysstat-collect-timer.conf` | `/etc/systemd/system/sysstat-collect.timer.d/80-nas-diagnostics.conf` | Change existing sysstat collection from ten minutes to one minute |
| `assets/nas/sysstat-collect-service.conf` | `/etc/systemd/system/sysstat-collect.service.d/80-nas-diagnostics.conf` | Add temperature/fan/load sampling after collection |
| `assets/nas/record-health.sh` | `/opt/server-context/assets/nas/record-health.sh` | Read CPU/ACPI/NVMe temperatures, fan RPM, available memory, load, power profile, boost, and NVIDIA runtime state; emit one journal line |

Temperature values in `nas-health` are millidegrees Celsius; fan values are RPM. `hwmon` numbering can change at boot, so use the sensor name and device mapping when comparing records. The sampler excludes GPU and Wi-Fi temperature probes, which can wake devices. Reload systemd and restart the existing collector timer after installing the overlays. Restart journald to load its drop-in and run `journalctl --sync`; a sudden hard freeze can still lose its final seconds, and a blocked storage/kernel path can prevent logging altogether.

The installed Ubuntu `kdump-tools` service already loads a crash kernel (`/sys/kernel/kexec_crash_loaded=1`) and NMI watchdog is enabled. No dump was present during inspection. Automatic panic/reboot settings were not added. Protected logs and pre-change hardware state are on the maintenance Mac under `~/ali/backups/nas-diagnostics-20261028`, outside Git and separate from the verified pre-LVM backup. Redundant NAS pre-LVM/storage/diagnostic copies were removed after byte verification against that independent material and runtime-dependency checks; the protected Mac originals remain intact. The day's sysstat file had a truncated record following the hard resets; preserve it before moving it aside and starting a new collector file.

`memtester` and `stress-ng` were added from signed Ubuntu repositories for bounded hardware checks. Both SSDs completed short self-tests without error. `memtester 32G 1` with `MEMTESTER_TEST_MASK=0x7` completed stuck-address, random-value, XOR, and subtraction checks on a locked 32 GiB allocation with exit status 0. Four stress-ng CPU workers using method `all` and verification completed 180 seconds with zero failures. The highest CPU temperature in ten-second samples was 72.375 degrees Celsius, fans reached approximately 2100-2400 RPM, and neither 85-degree temperature guard stopped a test. A userspace test checks only its allocated memory under the current power policy; it cannot clear all 64 GB or verify the previous boost/idle behavior. If freezing continues, boot an offline MemTest86 USB and test the two DIMMs separately when errors appear or the combined configuration remains unstable. Check the AC adapter, battery/connector condition, fan operation, and cooling path. Make subsequent CPU, NVMe, graphics, or firmware changes one at a time, preserve the failure evidence, and remeasure wall power before returning to a lower-power policy. Short tests and cutover acceptance do not resolve the freeze cause. Historical pre-LVM/diagnostic backups and the frozen ALI installation are retained, but none covers subsequent NAS application writes or its current private recovery scope.

```sh
ssh nas 'journalctl --list-boots; journalctl -k -b -1 --no-pager'
ssh nas 'journalctl -u sysstat-collect.service --since today --no-pager -g nas-health'
ssh nas 'sar -u -r -q; cat /sys/devices/system/cpu/cpuidle/current_driver'
ssh nas 'cat /proc/cmdline; cat /sys/module/processor/parameters/max_cstate'
ssh nas 'cat /sys/devices/system/cpu/cpufreq/boost; kdump-config show'
```

Shared docs synchronize with `SYNC_HOST=nas skills/server-operations/scripts/sync-docs.sh shared` from the pushed agent-config checkout. This creates `/opt/server-context`, `/opt/AGENTS.md`, and the login notice. `/root/AGENTS.md` links to `/opt/AGENTS.md`. Synchronize active NAS application docs separately when their contracts change; do not update frozen ALI application documentation or require ALI application maintenance as part of NAS work.

The user deferred router reservation, wired-network changes, and offline full-memory investigation. The application/gateway cutover and first external recovery package are accepted. Beyond the user-confirmed maintenance Mac browser flow, other device/browser CA trust, Origin logins, Aura client switching, and a production restore drill remain outstanding. Preserve frozen ALI materials, failed recovery stages and protected pre-existing Mac backups. Certificate renewal, security updates, time synchronization, TRIM, and diagnostics continue independently of the manual backup policy.
