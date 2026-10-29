---
name: server-operations
description: "Maintain the user's personal Linux servers and hosted projects, including SSH host ali, shared infrastructure, deployments, inventory, and server documentation."
---

<a id="服务器与多应用维护"></a>
# Server and Multi-Application Maintenance

Use this skill as the entry point for shared operations context, without relying on earlier conversations. Keep implementations simple, readable, and reproducible; improve the architecture to meet real needs rather than treating today's design as a permanent constraint.

<a id="先读什么"></a>
## What to read first

1. Always start with [Shared conventions](references/conventions.md) and [Current server and application inventory](references/current-state.md).
   For SSH host `nas`, also read [NAS laptop operations](references/nas-host.md); it is a separate host from `ali`.
   For SSH host `vps`, also read [VPS operations](references/vps-host.md); it is an AlmaLinux VM, not an Ubuntu application host.
2. Read the target project's `AGENTS.md`, `docs/README.md`, and `docs/OPERATIONS.md`, then read architecture/API/release documentation as the task requires. The inventory lists repository and server documentation locations.
3. For release, build, or testing strategy, first read [Local releases and on-demand validation](references/release.md). For changes, deployments, or documentation updates, you must read [Completing changes and documentation](references/maintenance.md); for new applications, migrations, or server replacement, also read [Rebuilding and adding applications](references/rebuild.md).
4. For release failures or troubleshooting, first consult [Common issues and shared solutions](references/common-issues.md) and directly follow any existing solution.
5. Use `personal-skill-management` for the skill itself or the personal instruction repository structure; `software-installation` for software installation/updates; and `python-environment` for Python environment operations. Do not duplicate their full workflows.
6. For public HTTPS, IP certificates, automatic renewal, or origin validation, read [Shared HTTPS](references/https.md) and handle all applications consistently.

7. For the portal, shared device authentication, resource declarations, backups of whole-server materials, or new data directories, read [Portal maintenance](references/portal.md) and update the affected applications' deploy/portal.json files as well.
8. For automatic cleanup of release materials, retention counts, failed batches, or cleanup locks, read [Automatic retention of release materials](references/retention.md).
9. When adding a website or changing icons, build paths, or shared authentication, apply the [Website icon conventions](references/conventions.md#website-icons-and-home-screen-shortcuts) by default and run the shared icon check; do not wait for a separate request for mobile icons.

<a id="authorization"></a>
<a id="授权改完告知还是先确认"></a>
## Authorization: proceed and report or confirm first

This is the sole authorization rule; project documentation should only link here. By default, complete the work and then report to the user. Stop to ask only for items in the "Confirm first" column below.

| Proceed and report when finished | Confirm first |
| --- | --- |
| Read-only checks: status, logs, configuration, hashes, network connectivity, and speed tests | Deleting, overwriting, or restoring real data and backups; choosing a recovery point; database migrations |
| Documentation for all projects and agent-config: editing, committing, pushing, and synchronizing server copies | Changes to public exposure, authentication, keys, deployment identities, or sudo permissions |
| Cleaning known junk: failed release leftovers, staging directories, and non-data files such as `._*` | Changes to root-managed release scripts, the shared Nginx server, or other applications' configuration |
| When the user requests implementation or deployment: validating the current feature, committing, pushing main, and releasing from the local machine | Downtime for other applications, host reboots, or additional costs |
| Fixing problems introduced by your own actions in the current task | Deploying, restarting, or fixing production when the user only requested inspection or diagnosis |

If the applicable column is unclear, use the left column when the action is reversible and does not touch real data. After completion, report the actions taken, results, and remaining items.

<a id="开始工作"></a>
## Getting started

- Inspect each repository's working tree and remote commits before connecting through a trusted SSH alias.
- Remote SSH commands do not automatically load remote instructions; explicitly read the target host's `/opt/AGENTS.md`, for example `ssh nas 'cat /opt/AGENTS.md'` or `ssh ali 'cat /opt/AGENTS.md'`. Neither the existence of AGENTS.md nor a login notice guarantees that every client will follow it.
- To view real production pages in a browser or from the command line, run `scripts/view-tunnel.sh`; see the [Shared conventions](references/conventions.md#agents-viewing-live-pages).
- Spot-check facts relevant to the task: listeners, units, Nginx includes, directory owners, versions, backups, and health. Run `bash /opt/server-context/scripts/inspect.sh` on the server for basic status without accounting records; verify cloud security groups separately.
- Documentation is a snapshot of the last verification, the live system is the actual state, and Git is the maintenance source. Investigate discrepancies rather than blindly overwriting the live system from documentation or declaring unexpected drift a new convention.

<a id="实施与收尾"></a>
## Implementation and completion

- Unless the user explicitly requests another language, write agent-authored specifications and maintenance documents in English, including `AGENTS.md`, project and server documentation, technical plans, operational runbooks, decision records, and handoff documents. Preserve exact source-language names, UI labels, quotations, matching literals, fixtures, and required user-facing content when translation would change meaning or behavior. This default does not determine the language of conversation, product copy, creative work, or other user-requested deliverables.
- Keep application-internal changes in that project. Before changing a shared layer, inspect every application in the inventory and list the affected configuration, code, data, releases, documentation, validation, and rollback points. Improve the design within the task's scope as needed.
- When any project encounters a common issue that may affect other applications (host, network, shared Nginx, common release/backup patterns, runtime dependencies, etc.), always document the solution in [common-issues](references/common-issues.md), covering every affected application. Project docs should retain only their own parameters and links, without maintaining separate copies.
- Complete the applicable criteria in [maintenance](references/maintenance.md). Update project or shared documentation only when the change alters a durable contract that those documents own; do not turn routine visual fixes or releases into operations, verification, or current-state logs. Replace outdated content and leave history to Git. Run `scripts/sync-docs.sh` after pushing only when managed documentation changed. For staged migrations, describe the actual coexistence of old and new components. If required synchronization is blocked, state what remains unfinished rather than reporting full completion.

<a id="来源与发现入口"></a>
## Sources and discovery entry points

- Shared source: `skills/server-operations/` in `Crashmere/agent-config`. The local checkout is usually `~/agent-config`; do not assume every computer uses `/Users/bytedance`.
- Shared server copy: `/opt/server-context/`. Its `SOURCE` records the source repository, commit, and synchronization time; it is not a second source that can evolve independently.
- Server entry point: `/opt/AGENTS.md`, linked from `/root/AGENTS.md` in root's login directory. Each application's `/opt/<app>/AGENTS.md` points to its project documentation.
- `/etc/update-motd.d/30-server-context` provides the interactive SSH notice on Ubuntu; `vps` uses `/etc/motd.d/30-server-context` through PAM instead. Do not force notices through sshd, global shell startup output, or restricted deployment forced commands; this can break noninteractive transfers.
- The local global AGENTS routes to this skill. Add offline/remote paths to each project entry point so discovery does not depend on one client.

The shared configuration template is [assets/nginx-apps.conf](assets/nginx-apps.conf), the server instruction entry point is [assets/AGENTS.md](assets/AGENTS.md), and the login notice is [assets/30-server-context](assets/30-server-context). `scripts/sync-docs.sh` synchronizes documentation copies. Changes to the Nginx template fall under "Confirm first" in the authorization table; reading the skill itself does not install or reload these files.
