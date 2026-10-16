<a id="重建服务器与新增应用"></a>
# Rebuilding Servers and Adding Applications

The goal is to restore the service setup and data at the backup point from Git documentation/source code and verified backups. See ServerPortal docs/RESTORE.md for offline private keys required by older encrypted packages and cloud-side prerequisites. The following is an operational sequence, not an installation script to run on an existing host without inspection.

<a id="1-准备来源和边界"></a>
## 1. Prepare sources and boundaries

- Obtain `Crashmere/agent-config` and every source repository in the application inventory; read the shared conventions, current state, and each project's docs.
- Establish whether this is a new empty server, a migration, or expansion of an existing host. The current baseline is Ubuntu LTS / amd64, 2 vCPU, about 2 GiB memory, and 40 GiB disk; there is no requirement to reproduce old kernel patches or all preinstalled software.
- Obtain independent administrator SSH access, the new host fingerprint confirmed through a trusted channel, and cloud security group management access. These secrets are not stored in Git; administrator identity cannot be reconstructed from public documentation.
- For rebuilding without data, explicitly create an empty database for each application. For migration with data, follow that application's final-backup/write-stop/restoration-validation plan; do not assume the user is willing to discard the old database.

<a id="2-建立共享底座"></a>
## 2. Establish the shared foundation

1. Verify OS/architecture, CPU/memory/disk, existing listeners and services, time synchronization, package sources, and update policy; record the actual choices in current-state.
2. Use `software-installation` to install Nginx, libvips-tools, libheif-plugin-libde265, and required system tools from official signed Ubuntu packages. Confirm python3 is available for portal declaration validation (standard library only, no additional Python packages). Do not copy the old cloud provider's internal package mirror. Applications build locally; do not install Go/Node/Docker/database services on the server.
3. Use Asia/Shanghai for displayed time and configure reliable NTP. Do not blindly change SSH/firewall settings on an existing host, especially in ways that lock out the administrator.
4. First run `scripts/sync-docs.sh shared` to create `/opt/server-context`, `/opt/AGENTS.md`, and MOTD, then link `/root/AGENTS.md` to `/opt/AGENTS.md` so the next maintainer can discover conventions immediately. Follow [Automatic retention of release materials](retention.md) to install tmpfiles configuration and create the shared lock before enabling application backup timers. Enable the cleanup timer after all applications are healthy and the preview has been checked.
5. Follow [Shared HTTPS](https.md): first create the HTTP challenge entry point with `assets/nginx-apps-bootstrap.conf`; install official Certbot and issue an IP certificate, then render `assets/nginx-apps.conf` to switch to HTTPS. Read all enabled sites first and save recoverable copies when resolving default-site conflicts; do not overwrite and break existing applications.
6. Create `/etc/nginx/app-locations` and enable the shared server at `sites-enabled/apps`. Install ServerPortal and the device-authentication include before enabling the final shared template. Until the portal is ready, use the bootstrap configuration without referencing a nonexistent auth include. Run `nginx -t`, then start/reload only after it succeeds.
7. Open only the SSH, HTTP (challenge and redirects), and HTTPS access required for this task in cloud security groups/host firewall; keep internal application ports on loopback. Decide whether to restrict SSH sources based on actual access needs; do not treat the old inactive UFW state as a security policy that must be copied.

<a id="3-重建或新增每个应用"></a>
## 3. Rebuild or add each application

- Read the initial installation process in project docs. Build from source or obtain trusted artifacts, then verify architecture and checksums. Exact build commands for each project (such as `make linux BASE_PATH=/ledger/`) belong in project documentation.
- Choose nonconflicting slugs, paths, ports, runtime identities, and directories for new applications; inspect the live system before recording them. Do not assume the next port is always available or borrow Ledger's data directory/release key.
- Create separate data/backups/config directories and run units as the application user. Clearly distinguish creating empty data from importing a verified backup.
- Add the application-owned Nginx location link and preserve the shared server. Verify bare-path redirects, page deep links, static resources, APIs, and write-origin validation; separately confirm reverse-proxy parameters when WebSockets/uploads are required.
- By default, equip new websites with a favicon, 180×180 PNG, shared head declarations, and exact anonymous GET/HEAD rules under the [Website icon conventions](conventions.md#website-icons-and-home-screen-shortcuts). Build and release icons with the application. Run the shared `scripts/check-site-icons.py` during deployment acceptance and verify authentication boundaries, without waiting for an additional user request.
- Start the application, enable startup on boot and backup scheduling, obtain the first backup through its unit with `systemctl start <app>-backup.service`, confirm Result=success, and check restoration to an isolated target; do not write test data to production.
- The project must have `AGENTS.md` and a docs entry point covering at least responsibilities/business conventions, architecture, runtime directories, configuration, startup and health, data model, backup/restoration, release/rollback, diagnostics, and known limitations.
- Add a complete entry to the shared application inventory and update the host state and shared configuration templates if they actually changed. Check that all existing applications remain healthy and that the new location does not take over an existing path.

New applications must integrate with the [portal declaration protocol](portal.md): local validation, pre-release checks, post-release synchronization, and a receipt for the loaded hash. The first declaration release automatically creates the registry.d link. Synchronize the shared validation script before starting a portal that uses the registry directory.

<a id="4-恢复本机发布"></a>
## 4. Restore local releases

Follow [Local releases](release.md) to prepare the maintenance computer's tools, trusted SSH access, and local private keys. Create a restricted identity and install fixed release scripts for each business application; retain administrator deployment for the portal. setup-deploy.sh configures public keys; GitHub stores no production Secrets. Do not directly enable old CI public keys restored from backups; replace them with the current maintenance computer's public key.

Build locally, deploy, and verify health one application at a time. Normal program releases synchronize the application's validated portal.json; administrators still install units, Nginx configuration, and release scripts, while sync-docs.sh synchronizes documentation.

<a id="5-验收与交接"></a>
## 5. Acceptance and handover

- All applications: direct and proxied health, page deep links and resources, expected login/public-access boundaries, runtime identities and write permissions, boot enablement, backup/restoration, and local release results.
- Shared layer: no port conflicts, correct Nginx syntax and request handling, existing applications unaffected, and no unintentionally exposed internal ports. Spot-check both service logs and application logs.
- Documentation: update the actual OS/resources/software/network/application inventory to the new server state and remove old host facts; update project IPs/paths/commands/configuration/installation scripts together. Explicitly mark items without sufficient evidence as unverified.
- Run `scripts/sync-docs.sh` after pushing all repositories and confirm discovery entry points work. Do not mark applications as rebuilt if credentials or data are missing or acceptance is incomplete.

<a id="可以改进但尚未实施的方向"></a>
## Possible improvements not yet implemented

Cloud backup console retention-policy verification, availability alerts, capacity management for other data, more granular permissions, domains, and similar improvements may be evaluated according to user needs. This is not a mandatory task list. After implementing an item, reflect it in conventions/current-state/all affected projects and remove its "not implemented" description. If the current need does not require it, do not build additional systems just because documentation suggests them.
