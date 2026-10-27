<a id="共享部署约定"></a>

# Shared Deployment Conventions

These are the baselines currently in use. They may evolve when supported by evidence and a migration plan; do not add frameworks, containers, database services, or orchestration platforms merely for uniformity. Do not turn project-specific behavior into a mandatory requirement for all projects.

<a id="职责划分"></a>

## Responsibilities

| Layer | Maintained in | Responsibility |
| --- | --- | --- |
| General agent behavior | agent-config/AGENTS.md | Safety boundaries and skill routing; no application details |
| Shared server | This skill's references and assets | Host state, application inventory, shared entry points, rebuilding, and cross-project rules |
| Individual project | Project AGENTS.md, docs, and deploy | Business conventions, runtime configuration, data, tests, deployment, and recovery |
| Live environment | Configuration/state under /etc and /opt | Actual operation; changes must be written back to the owning source and documentation |

Solutions to common issues also have a single source: document issues that may affect multiple applications in [common-issues](common-issues.md), listing parameters by application; project documentation links there instead of copying procedures. Keep issues that affect only one application in that project.

Each configuration has only one maintained source. Server copies and necessary distribution materials are not additional sources. This skill owns the global Nginx server template; each application owns its locations. Do not place shared configuration in a business application project.

<a id="网络入口"></a>

## Network Entry Points

- Access currently uses HTTPS on port 443 at the public IP, with a trusted Let's Encrypt IP certificate. Applications share Nginx and are routed through `/<app>/`; public HTTP port 80 remains available for ACME validation and returns 308 redirects to the fixed HTTPS address for other requests. For certificates, renewal, and local inspection entry points, see [Shared HTTPS](https.md).
- Each application listens only on its own `127.0.0.1:<port>` and registers the port in the application inventory. Check `ss -ltnp` before adding one; do not assume the inventory is complete. Do not open a separate public port for each application.
- The shared configuration is `/etc/nginx/sites-available/apps`, enabled through the link at `sites-enabled/apps`. The HTTPS server and the loopback-only HTTP inspection server include `/etc/nginx/app-locations/*.conf`, with each application's link pointing to its own configuration. The HTTPS root and unassigned paths redirect to `/portal/`; unassigned paths on the loopback-only inspection server still return 404.
- When changing the shared server, check every location's matching, rewriting, Host, forwarded headers, static assets, and deep links. Whether the trailing slash in `proxy_pass` strips the prefix is part of each application's interface contract; do not copy it mechanically.
- Different paths on the same IP still share a browser origin and do not provide security isolation. Public access is protected centrally by ServerPortal device authentication; authorized devices share business data, and applications do not distinguish account roles. New applications must inherit shared authentication and the renewal response headers for valid device cookies. Check inheritance when changing an application's add_header directives; see portal maintenance for the procedure.
- When changing domains, TLS, shared authentication, or reverse proxies, check every application's build prefix, absolute URLs, Origin/Cookie handling, health checks, deployment, and documentation. Obtain confirmation first if the access method changes.

<a id="agent-查看线上真实页面"></a>

## Agents Viewing Live Pages

The public entry point requires a device cookie. The agent's browser and command line are not authorized, and the agent must not extract cookies from the user's browser. Always view live pages through an SSH tunnel to the loopback-only HTTP inspection entry point: run `scripts/view-tunnel.sh` locally (idempotent; reuses an existing working tunnel, and running it again after disconnection recreates it), then open `http://127.0.0.1:18180/<app>/`. Paths, prefixes, and deep links match public access. Use `stop` to close the tunnel and `status` to inspect it.

- This relies on existing SSH trust and does not change public exposure or shared authentication. The local port listens only on 127.0.0.1.
- The portal at `/portal/` itself still requires login and is not accessed this way.
- These pages show real production data. Some applications' origin checks (verified for Ledger) allow write requests through the tunnel, so default to browsing, screenshots, and read-only requests. Obtain confirmation under the authorization table before writes such as saving, deleting, or importing; use a synthetic environment for functional write tests.

<a id="网站图标与手机桌面入口"></a>

## Website Icons and Home Screen Shortcuts

Confirmed by the user on 2026-09-28: automatically provide all of the following for every future website from its first delivery, as default work for a new project rather than leaving separate configuration to the user.

- Provide the site's own favicon and an opaque 180×180 PNG. Explicitly declare `rel="apple-touch-icon" sizes="180x180"` in the HTML head shared by all pages. Use the correct application prefix in paths and inspect the actual build output; do not rely on a fallback icon at the origin root. Keep the generation script and graphic sources in the project, and package the PNG with the build so the server needs no graphics build tools.
- When shared authentication is enabled, also configure anonymous GET/HEAD access to brand icons in the project's Nginx location. Enumerate only specific names; for builds with hashes, allow only strict patterns for the corresponding icon names. Keep authentication on other files, pages, APIs, and uploaded media; do not exempt the entire assets/static directory. The portal's own public login assets are handled by its Web layer.
- For applications that already use a manifest, the public manifest and every icon it references must also be independently accessible; check start_url/scope. There is no need to introduce a manifest or Service Worker solely for an iPhone icon. Do not put business data or secrets in a manifest.
- After deployment, run `scripts/check-site-icons.py --page-url <local-upstream-page> --public-url <HTTPS-app-page>`: it automatically parses icons and the manifest from real HTML and anonymously checks GET/HEAD, types, PNG dimensions, and manifest icons. It can run on the server over SSH without a login password. The script supports any new application without maintaining a central icon list. The page source must return HTML directly; for the portal, use the local `/portal/login` (which shares its head with logged-in pages), and do not treat a redirect response as a page.
- Changes to Nginx rules also require checking files and methods that should not be public in a synthetic environment (existing cases are in `scripts/test-public-icons.py`; extend the cases for new applications), followed by checks of production page redirects and unauthorized API responses. Icon checks are part of deployment acceptance, and failures must be fixed. Invoke the trusted shared scripts rather than copying their validation logic.
- Record actual resource paths, generation methods, and links to the shared rules in project AGENTS and operations documentation. Confirm the result of adding to the home screen separately on a real iPhone; do not represent desktop browser or HTTP checks as real-device tests. For troubleshooting, see [common-issues](common-issues.md#missing-iphone-home-screen-icons-after-shared-authentication).

<a id="目录身份和进程"></a>

## Directories, Identities, and Processes

Source repositories and local directories use the application names `Ledger`, `FeeTable`, `FabricWorld`, `RecipeBox`, `Yuyan`, `ServerPortal`, `AICalendar`, and `Aura`; server application directories, URL prefixes, runtime/deployment users, and systemd units use the corresponding lowercase names. Repository name capitalization does not change runtime paths.

```text
/opt/server-context/      Controlled copy of shared context; no credentials or runtime data
/opt/<app>/
  AGENTS.md              Project maintenance entry point
  bin/                   Programs and maintenance scripts
  config/                env, units, and application Nginx configuration
  data/                  Application data
  backups/               Consistent backups
  docs/                  Project documentation copies and source markers
  releases/              Versions and deployment results retained as needed
```

- Give each application a separate runtime user. Root manages programs, scripts, and configuration; the runtime user writes only to explicitly designated directories such as its own data and backups. Default data/backup permissions are 0700, with stricter permissions for sensitive configuration; do not treat 0644 as a general permission for secrets.
- Use systemd for persistent operation and startup at boot. Keep unit sources in the application's config directory and link them through `/etc/systemd/system/`. Logs go to the journal; locate request logs according to application/shared-entry-point responsibilities.
- Add restrictions such as `NoNewPrivileges`, `ProtectSystem`, and `ReadWritePaths` as needed, and verify that they do not prevent real operation. Do not copy an unsuitable sandbox.
- The current business applications and portal are all single-file Go programs built locally. The server needs neither Docker, Go/Node build environments, nor a self-hosted runner; FabricWorld and RecipeBox additionally require the system package libvips; Aura uses libvips, ExifTool, and FFmpeg. Aura also bundles a locally built Swift PhotoKit companion; the Mac release build requires Apple Command Line Tools. Do not install Node on the server: build frontend assets locally and embed them in the program. Obtain user confirmation first for a new application that truly requires a Node runtime. New applications may choose technology according to their dependencies; when introducing shared runtimes/container platforms, record the impact on all applications and the maintenance cost.
- Do not remove host tools, cloud-provider agents, scheduled tasks, or user files outside the task. Identify the source of unknown units first.

<a id="数据备份与发布"></a>

## Data, Backups, and Deployment

- SQLite is an in-process library, not a global service. Each application uses separate files; applications must not share a ledger. Whether a new project uses SQLite depends on its requirements.
- Do not copy only the main file of an active WAL database; use the application's consistent-backup tool. Confirm the recovery point and data loss before restoring, and preserve the current state in a recoverable form. Do not handle a startup failure by creating an empty database.
- A backup unit's sandbox must not split the source and destination into separate mount points, or hard links will fail; see [common-issues](common-issues.md#photo-hard-link-backups-fail-in-a-systemd-sandbox). After enabling the timer, run the backup through the unit once and confirm Result=success.
- For every application with data, register its backup tool, schedule/time zone, retention policy, recovery steps, verification method, and off-host backup status. Shared documentation provides only an overview; exact operations belong in project docs.
- Business applications use separate restricted deployment identities and dedicated local keys, not the administrator's private key or unrestricted sudo. ServerPortal continues to use administrator SSH because it manages a root collector; see [Local Deployment](release.md) for the exact boundaries. Keep SSH host identity verification on all connections.
- Normal deployments do not include production data. Design schema updates for compatibility/rollback, and do not describe program rollback as database rollback.
- Control build, backup, and deployment resource use on the shared machine. Build on the maintenance computer and deploy one application at a time; do not introduce unnecessary concurrency infrastructure for a single-user service.

<a id="文档卫生"></a>

## Documentation Hygiene

- Clearly distinguish "currently in use," "user confirmed," "not yet verified," and "needs improvement." Record verification dates and provide query methods for volatile values rather than accumulating process IDs, daily filenames, or transaction counts.
- Do not put combinations of server public addresses and unauthenticated paths, private keys/tokens, complete sensitive configurations, real accounts, or backups in public repositories. Use SSH aliases and secret names; required credentials are provided separately by the user or an existing secret-management system.
- Git backs up documentation and configuration templates, not data or secrets. Rebuilding aims to reproduce the service setup; it does not promise to recover ledgers, SSH authorizations, or cloud security groups from nothing.

<a id="门户资源契约"></a>

## Portal Resource Contract

Each application owns deploy/portal.json, describing directory purposes, databases/media, backups, ports/units, access paths, and APIs. When changing related resources, update the declaration, project docs, and shared inventory in the same commit. Local deployment uses a trusted shared validator to automatically preflight, publish the declaration, and check the portal receipt. The portal dynamically reads registry.d and does not maintain a central array of application paths. New services still need explicit resource purposes and backup contracts; ordinary additions or removals of data do not require declaration changes. See [Portal Maintenance](portal.md) for the procedure. Treat current-state as the authority on activation status; integration files in source do not mean production has already switched.

<a id="网页键盘与焦点"></a>

## Web Keyboard and Focus

Confirmed by the user on 2026-09-30: for all existing and future web services, block Tab / Shift+Tab from moving focus between page controls by default, and remove outlines, shadows, borders, or color highlights when controls receive focus. Add exceptions only when the user explicitly requests a special behavior. The global entry point is maintained in agent-config/AGENTS.md; this section records how server projects implement it.

- Install a shared keyboard policy at application startup, covering the home page, forms, menus, dialogs, and lazy-loaded pages, so component libraries or focus-trapping logic do not take over ordinary Tab again. Do not implement it through blur, disabled controls, or hidden text carets.
- Preserve Ctrl/Command/Alt combinations, IME composition, and business selection states. Ledger's existing behavior is a user-approved exception: preserve Tab switching between the workbench's “明细” and “洞察” views, cycling among the three fields in single-entry input, and panel focus management. Preserve editing operations such as indentation and table-cell navigation in Yuyan's document body and code areas.
- Verify actual keystrokes and styles after focus; check mouse-click text input, existing shortcuts, dynamic dialogs, and desktop/narrow-screen scenarios. Do not treat this user choice as an accessibility defect and automatically restore Tab navigation or focus highlights.

<a id="个人项目验证标准"></a>

## Validation Standards for Personal Projects

Deploy after locally verifying the functionality changed in this task. Do not require a full historical regression suite or add or retain permanent tests by default. Temporary scripts may be deleted after use; retain necessary type checks in the build. Ordinary interaction failures can be fixed or the program rolled back; validate bulk rewrites/deletions, migrations, overwrite imports, and backup restoration on an isolated copy first. Keep deployment locks, backups, validation, health checks, and rollback on failure. For specific entry points and environments, see [Local Deployment](release.md).
