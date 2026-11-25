# Common Issues: Host, OS, systemd, SQLite, and Drivers

Shared solutions for host OS differences, systemd sandboxes/caches, Snap, network boot, GPU drivers, freezes, and SQLite locks. See the [symptom index](common-issues.md) for all topics.


## Persistent SQLite snapshot locks with healthy reads

On `nas`, Lilt returned HTTP 500 for playlist creation while library reads and `/healthz` still succeeded. Its main-service journal already contained repeated `database is locked (517)` failures before the attempted write, and the lyrics-worker heartbeat was unavailable. SQLite error 517 is `SQLITE_BUSY_SNAPSHOT`; a successful read or connection ping does not establish that the application's connection can write. Restarting only Lilt restored playlist creation, uploads, membership appends and the worker heartbeat with the same program, configuration and data paths. The transaction or cursor responsible for the stale snapshot has not been identified; this is a recovery procedure, not a root-cause fix. Other SQLite applications on `nas` are potential diagnostic users, not confirmed affected instances; `ali` and `vps` remain gateways.

Capture the affected service's journal and inspect incomplete uploads and active processing before recovery. Apply the shared authorization table, then hold the shared maintenance lock and the application's deployment lock while restarting only that service. For Lilt on `nas`:

```sh
flock -s -n /run/lock/server-maintenance.lock \
  flock -n /run/lock/lilt-deploy.lock systemctl restart lilt.service
```

Lilt's linked lyrics worker restarts with it. Preserve acknowledged uploads and resume the original batch; do not delete SQLite WAL/SHM files, restore a database, redirect data paths or retry an uncertain create without first checking whether it succeeded. Verify main health, the worker heartbeat and the originally requested write, then check the journal for recurrence. If the error returns, investigate transaction and cursor lifetime in both processes rather than repeatedly restarting them or increasing `busy_timeout`.


## Distribution-specific inspection and login notices

The `vps` image is AlmaLinux, whereas `ali` and `nas` use Ubuntu. An absent UFW executable or Ubuntu Nginx directory does not establish a host failure. The shared `inspect.sh` selects the installed firewall tool and inspects Nginx directories only when present. Verify both active firewall rules and cloud-side access separately.

Ubuntu runs `/etc/update-motd.d` scripts; AlmaLinux's SSH PAM configuration uses `pam_motd.so` and reads static `/etc/motd.d` snippets. `sync-docs.sh` maps the notice according to `SYNC_HOST=vps`; it must not introduce unconditional shell startup output, which can break command and file transfers. All applications on `ali` keep their existing notice and configuration; this difference concerns `vps` host bootstrap only.


## Host-wide stale unit-cache warnings after Snap refresh

On `nas`, `NeedDaemonReload=yes` appeared on all seven business services, Portal Web/collector, Nginx, both tunnels, SSH, chrony, and journald while those services remained healthy. A completed automatic `snapd` refresh added its mount links under `multi-user.target.wants` and `snapd.mounts.target.wants` just after systemd finished reloading. No persistent loaded fragment, drop-in, or generator source had changed afterward. The unit lookup cache was stale; the warning did not identify an unapplied Portal service change. The active `ali` and `vps` gateway services were unaffected.

Before clearing a host-wide warning, inspect concrete units' `FragmentPath`, `DropInPaths`, `SourcePath`, and `NeedDaemonReload`, compare effective settings with their current definitions, and check the unit lookup directories and relevant package-operation history. Use the last completed PID1 reload's JSON journal `__REALTIME_TIMESTAMP` when comparing modification times: ordinary second-resolution output cannot distinguish links created milliseconds after that reload from its own generated files. Runtime `/proc` and transient `/run` records are not persistent source edits. Review unexplained configuration changes before loading them.

Once the differences are accounted for and `systemctl list-jobs` shows no pending jobs, run `systemctl daemon-reload` under the shared NAS maintenance lock. This refreshes unit definitions and dependencies without restarting services. Confirm `NeedDaemonReload=no`, no failed units, and unchanged main PIDs, start timestamps, and restart counters for business services, Portal, Nginx, tunnels, and management services. Then check NAS LAN HTTPS and both gateway entrances. The NAS fix preserved all 15 checked service processes; no unit edit, service restart, or host reboot was needed.


## GPU kernel caches in a read-only service sandbox

Lilt's NAS singing inference completed on CUDA but PyTorch warned that `/opt/lilt/.cache/torch/kernels` could not be created, disabling kernel caching for every new inference process. Changing the cache environment alone still failed when the selected directory did not exist. Keep the runtime and home read-only; set `PYTORCH_KERNEL_CACHE_PATH` and `CUDA_CACHE_PATH` to private application-owned analysis subdirectories and create them as the runtime user before worker startup. Lilt's unit uses `ExecStartPre` for this step alongside its existing Matplotlib/Numba cache settings. Synthetic inference under `lilt` then populated the kernel cache without the warning. Apply this diagnosis to another GPU application when its logs identify a cache-path failure; driver changes and broader filesystem permissions are not needed.


## Whole-host freezes with no retained panic

On `nas`, both the local console and network have stopped responding, including an overnight idle episode; the user also reports freezes under Windows. Retained logs contained no conclusive panic, OOM, or storage failure. Preserve journals and hardware state before further resets, check activity and SMART/self-test evidence, and investigate hardware/firmware alongside Linux drivers when the symptom crosses operating systems. An abruptly ending journal does not identify the exact freeze time or prove a thermal, memory, or driver cause.

The NAS mitigation and diagnostic sources are maintained in [freeze diagnostics](nas-host.md#freeze-diagnostics): balanced firmware profile, disabled boost, C1 idle restriction, and persistent minute health records. A later home check showed roughly 35 hours of uninterrupted idle operation and no minute-sampling gap beyond 61 seconds. This does not identify the cross-OS freeze cause or establish loaded-service reliability. The user deferred further investigation and accepts proceeding with migration under that residual risk. If freezing recurs, preserve available evidence and inspect hardware/firmware alongside drivers; do not automatically reboot or change several power settings together.


## Network startup waits for an unplugged interface

On `nas`, Wi-Fi acquired an address but `systemd-networkd-wait-online.service` timed out after two minutes, leaving the host degraded. The installer configured the unplugged Ethernet interface as required, and Netplan generated a wait-online command that waited for it as well as Wi-Fi. This host-level delay would affect every application depending on `network-online.target`.

Mark the unused Ethernet interface `optional: true` in Netplan and enable `dhcp4` so it works when a cable is connected. Keep the working Wi-Fi configuration and its credentials intact. The source for this host is `assets/nas/ethernet.yaml`; install it mode 0600 at `/etc/netplan/80-nas-ethernet.yaml`, run `netplan generate`, then `systemctl daemon-reload`, `networkctl reload`, and `networkctl reconfigure enp2s0`. Reset and start the failed wait-online unit, then verify Result=success and a new SSH connection. This procedure avoids restarting the active Wi-Fi interface.


## NAS asset script fails with 203/EXEC

On `nas`, `nas-lan-tls.service` failed with `203/EXEC` and `Permission denied` for an existing root-owned `renew-lan-tls.sh`. Documentation synchronization installs assets as mode 0644, so a unit cannot execute the script directly. [The maintained TLS unit](../assets/nas/nas-lan-tls.service) invokes `/bin/bash` explicitly; the script requires Bash's `pipefail`. A one-off `chmod` would be reset by the next documentation sync. NAS power and health units already invoke `/bin/sh` and need no change.

Install the corrected unit after source synchronization, verify it with `systemd-analyze verify`, reload systemd, and run the renewal service. Confirm `Result=success`, a valid leaf/CA chain, and the enabled timer. All NAS applications share this LAN certificate; ALI/VPS public renewal is unaffected.


<a id="官方-snap-下载过慢"></a>

## Official Snap Downloads Are Too Slow

A single connection from the server to the Snap Store may run at only tens of KB/s. During the 2026-09-27 Certbot installation, core24 and snapd completed, while the 75 MB Certbot package remained slow. The issue was the download path, not a post-installation startup failure.

On a trusted workstation, prefetch the package for the exact architecture and revision from the same Snap Store download URL, using ranges if needed. Verify the complete file against the store metadata's SHA3-384, transfer it to a separate staging directory on the server as `certbot_<revision>.snap`, and run `snap download certbot --revision=<revision> --target-directory=<directory>` there. This verifies and reuses the complete file while downloading the official assertion chain. After confirming that the `.assert` file exists, cancel the still-incomplete duplicate download and wait for it to exit, then run `snap ack <file.assert>` and `snap install <file.snap> --classic`. Never use `--dangerous` to skip signature verification. Check the version, publisher, stable tracking, and renewal timer, then remove only these identified installation staging files while retaining rollback configuration.

This method replaces only file transfer; official signatures and snap still manage installation and updates. Do not delete or rewrite snapd's internal cache, partial files, or state database. If the service is actually failed, troubleshoot it from the logs first.


## NVIDIA modules cycle after replacing Nouveau live

On NAS, a live switch from Nouveau to Ubuntu's NVIDIA server driver can leave queued udev `remove` events interleaved with new `add` events. The packaged `71-nvidia.rules` runs `modprobe -r` for dependent modules on driver removal; stale events can unload the newly loaded base driver, causing another add/remove cycle. Symptoms include repeated `nvidia-drm` loading/unloading, persistence daemon restarts, intermittent `nvidia-smi` failures, and CUDA initialization errors. Inspect the kernel journal and udev worker commands before treating this as a GPU hardware failure.

For a confirmed installation-time cycle with no GPU consumers, temporarily copy `/usr/lib/udev/rules.d/71-nvidia.rules` to the same basename under `/run/udev/rules.d/`, omitting only the `ACTION=="remove", DEVPATH=="/bus/pci/drivers/nvidia"` lines. Reload udev rules and drain events with a bounded `udevadm settle`, load `nvidia` and `nvidia_uvm`, then drain events again. Remove the temporary override and reload the original rules after the device is stable. Verify CUDA/NVENC and singing inference under the actual application identities and confirm that kernel events stop cycling. Leave package-owned rules unchanged. This procedure affects NVIDIA consumers on NAS, currently Aura, Curio and Lilt; the internal display remains on AMD. Future driver transitions should prefer a separately authorized reboot when live unload prerequisites are not met.
