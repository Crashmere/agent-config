<a id="服务器维护入口"></a>
# Server Maintenance Entry Point

Before operating this server or deploying a new application, read `/opt/server-context/SKILL.md`, then follow its navigation to the shared conventions, current application inventory, and target project documentation.

- Shared documentation source: `skills/server-operations/` in `https://github.com/Crashmere/agent-config`. The server's `/opt/server-context/` is a synchronized copy; see its `SOURCE` for provenance.
- Project details come from each project's own repository. The current projects are Ledger, FeeTable, FabricWorld, RecipeBox, Yuyan, ServerPortal, and AICalendar. Use the shared application inventory to locate `/opt/<app>/AGENTS.md` and `/opt/<app>/docs/README.md`; provenance is in the corresponding `docs/SOURCE`.
- Read the current state, then verify it with read-only checks. Do not assume the live system is unchanged just because a service is documented. Do not read or print unrelated credentials/business data.
- Use only the authorization table in `/opt/server-context/SKILL.md` to decide what to complete and report versus what needs confirmation first. Documentation maintenance, known-junk cleanup, and applying existing solutions all belong in the proceed category.
- Before changing shared entry points, ports, runtimes, permissions, backup plans, or release plans, assess every application in the inventory rather than fixing only the new project.
- By default, block Tab / Shift+Tab from moving focus between web controls and remove focus highlights. See "Web keyboard and focus" in `/opt/server-context/references/conventions.md` for user-requested exceptions and validation scope; do not restore browser defaults on your own.
- For release failures or troubleshooting, first consult `/opt/server-context/references/common-issues.md`. Document solutions to issues that may affect multiple applications there; retain only project-specific parameters and links in project documentation.
- For every change, update the owning source configuration and current documentation. After committing and pushing, run agent-config's `skills/server-operations/scripts/sync-docs.sh` locally to synchronize server copies. A server-only change without updating the repository is incomplete.
- Keep project databases, backups, private keys, and tokens out of Git. Business repositories and shared context are public; the ServerPortal repository is private. All source repositories must still exclude public addresses, real data, and secrets.

Note: noninteractive SSH does not automatically load this file. Agents performing remote operations must explicitly run `cat /opt/AGENTS.md`; the interactive login notice only aids discovery.
