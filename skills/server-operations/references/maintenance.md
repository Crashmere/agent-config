<a id="变更与文档闭环"></a>
# Completing Changes and Documentation

Use only the [authorization table in SKILL.md](../SKILL.md#authorization) to decide what to do directly and what needs confirmation first. This document covers how to complete the work.

<a id="每次维护的完成条件"></a>
## Completion criteria for each maintenance task

1. Read the current inventory, target project entry point, and relevant configuration. Check each repository for uncommitted changes and preserve other people's work.
2. Implement and validate only the behavior affected by the change, plus actual dependents when a shared component changes. Use synthetic environments for tests that write data; acceptance checks in production must be read-only. Stop after the focused checks pass unless a failure, new change, or unresolved concrete risk justifies more work.
3. Update documentation only when it preserves durable knowledge that a maintainer or agent will need. Put stable code, API, format, or interaction contracts in project design/reference docs. Update project operations docs only for changes to runtime, data layout, directories, services, permissions, backup or recovery, authentication or access, deployment mechanisms, or durable diagnostics. Keep long-lived verification evidence only for high-risk or contract-level behavior such as migrations, bulk data operations, security, recovery, compatibility, or a plausible regression; do not append routine release checks or visual-fix records. Update shared conventions and current-state only for shared architecture, inventory, or durable operational contracts. Purely visual, cosmetic, and other reversible low-impact changes do not by themselves require operations, verification, or current-state edits. Record issues and solutions that may affect multiple applications in [common-issues](common-issues.md), keeping only links in affected projects. Replace old descriptions, remove obsolete content, and leave history to Git. Do not put credentials, databases, backups, or accounting statistics in documentation or Git.
4. Check links, configuration syntax, sensitive content, and `git diff --check`, then commit and push. Application pushes only back up source code; switching production requires an explicit local make deploy.
5. Run `scripts/sync-docs.sh` only when its managed project or shared documentation changed. The final report must list the layers changed, whether runtime or data changed, focused validation results, and unfinished items; when no durable documentation contract changed, state that no documentation synchronization was needed only if that distinction helps explain the result.

<a id="哪些变更需要跨项目处理"></a>
## Changes requiring cross-project work

| Change | Must also check/update |
| --- | --- |
| Public entry points, TLS, authentication, IP/domain | Every application's URLs, resource/route/API prefixes, Origin/Cookie, health checks, local SSH deployment authorization and host fingerprints, and access instructions |
| Shared directories/permissions/runtimes | Units, startup commands, writable directories, backups, recovery, releases, documentation entry points, and installation materials for each application |
| Nginx server/includes/proxy headers | All locations, redirects, deep links, APIs, uploads/WebSockets where present, and logs |
| Backup or release mechanisms | Tools, schedules, rotation, recovery drills, permissions, and failure handling for every application using the mechanism |
| Adding/retiring applications | Application inventory, port and path allocation, users/units/entry points, and project docs; resource deletion requires a separately defined scope |

Before implementation, list the common target, affected items, execution order, and rollback plan. Implementing a new architecture alone does not mean the entire server has been unified. Document transitional states only while components actually coexist, then remove them when complete; do not maintain a "v1/v2/v3 design comparison table."

<a id="文档同步"></a>
## Documentation synchronization

Run from a local checkout whose commits have been pushed (the bash 3.2 bundled with macOS is sufficient):

```sh
~/agent-config/skills/server-operations/scripts/sync-docs.sh           # shared + all projects
~/agent-config/skills/server-operations/scripts/sync-docs.sh Ledger    # synchronize only the listed targets
~/agent-config/skills/server-operations/scripts/sync-docs.sh --check   # read-only: drift, lag, junk files
```

The script:
- Exports only managed files from pushed commits: for shared, all files under `skills/server-operations/`, plus `/opt/AGENTS.md` and the login notice; for projects, `AGENTS.md` and `docs/*.md`. Skips a target with uncommitted or unpushed documentation changes.
- First compares the server copy with the commit recorded in its `SOURCE`; stops and shows differences if they disagree. Bring live edits back into the repository first, confirm them, then use `--force` to overwrite.
- Installs files owned by root, with mode 0644 for docs and 0755 for scripts and the login notice. Deletes managed files present in the old commit but absent from the new one, and removes `._*` from copy directories. Finally writes `SOURCE`, verifies hashes file by file, and cleans staging directories.
- Does not change programs, units, Nginx, databases, or `current-commit`.

`PROJECTS_DIR` specifies the project checkout directory (default `~/ali`); `SYNC_HOST` specifies the SSH alias (default `ali`). With no arguments, the project list comes from the server's existing `/opt/*/docs/SOURCE` files. Pass the project name explicitly for a new application's first sync; the script creates missing directories.

<a id="发现机制与验证"></a>
## Discovery and verification

- Synchronize local global AGENTS and client links for this skill through the `personal-skill-management` repository workflow; do not create a separate set of client discovery rules.
- `/root/AGENTS.md` helps agents working as root discover instructions on the server; `/opt/AGENTS.md` helps agents working under /opt; application entry points also provide project documentation.
- Tools load AGENTS differently, so do not claim every agent must read it upon connecting. Local routing must explicitly direct remote SSH commands to read it; interactive SSH MOTD is only a notice.
- On initial entry point installation, confirm `/root/AGENTS.md` does not exist before linking it to `/opt/AGENTS.md`, and confirm the MOTD destination has no conflict before installing it. The synchronization script maintains them afterward.

<a id="提交前的最小检查"></a>
## Minimum checks before committing

- Check skill frontmatter, shell syntax with `bash -n`, and `git diff --check`; run new scripts once for real (use `--check` for the synchronization script).
- Search for accidental tokens/private keys/production addresses/real data; do not print credential contents to scan for secrets.
