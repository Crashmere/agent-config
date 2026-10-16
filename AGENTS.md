# Global Agent Instructions

## Python environment policy

- Never install Python packages into the global environment unless the user explicitly requests it.
- Use the `python-environment` skill whenever Python execution requires third-party packages, environment creation or selection, dependency changes, or interpreter/package troubleshooting.

## Instruction management

- Use the `personal-skill-management` skill when organizing agent instructions or creating and maintaining the user's own skills and their `agent-config` GitHub repository.
- When a personally maintained skill or its scripts prove incorrect during real use, fix the immediate task, then use `personal-skill-management` to reassess and update the skill so the repository remains accurate.
- If a required skill cannot be found or loaded, quickly investigate its likely source, pause the dependent workflow, and report the missing skill and findings to the user instead of silently substituting another process.

## Software installation policy

- Prefer official or first-party software sources.
- Use the `software-installation` skill for software installation, upgrade, removal, or installation troubleshooting.
- On macOS, assess each software removal individually: prefer a complete official uninstall process when available and use the `mole` skill as a supplement; otherwise use Mole when appropriate. Use Mole for storage cleanup, except for straightforward deletion of explicitly identified files or directories.
- When the user explicitly requests installation, complete it and verify the result unless a material risk or unresolved choice requires confirmation.

## General workflow

- Keep changes safe, scoped, and relevant to the task.
- Explain destructive actions and ask for confirmation before running them.

## Testing and investigation discipline

- Minimize unnecessary tests and test runs. Before adding or running a test, identify the concrete behavior or failure it would check, whether that situation can realistically occur, how likely it is, and whether detecting it justifies the effort. Skip tests without a meaningful answer.
- Do not add tests merely to increase coverage or demonstrate that testing happened. Avoid unit tests that mirror the implementation, trivial assertions, hash or snapshot comparisons without a real integrity requirement, and elaborate fixtures for impossible or extremely unlikely states.
- During normal development, treat sufficiently unlikely hypothetical failures as acceptable risk. Consider them briefly, then move on instead of spending time on speculative tests or deep investigation. Examine unusual conditions and implementation details thoroughly when an actual failure, reproducible symptom, or concrete evidence makes that investigation relevant.
- Prefer the smallest check that verifies the requested behavior, reusing existing checks when useful. Simple documentation, cosmetic, and other reversible low-impact changes do not automatically need tests. Add regression tests only when they protect against a plausible recurrence of a real problem.
- Stop once the relevant checks pass. Expand or repeat testing only when new changes, failures, or unresolved concrete concerns justify it. Honor explicit test requests and mandatory project checks within their applicable scope.

## Web keyboard and focus policy

- For all web services developed or maintained for the user, block ordinary Tab and Shift+Tab from moving focus between page controls by default, including menus, forms, dialogs, and dynamically loaded pages. Change this only when the user explicitly requests a different behavior.
- Do not show control focus highlights: remove browser focus outlines and focus-only shadows, border/color changes, and similar decoration unless the user explicitly requests them. Keep text carets, text/content selections, and business selection states working.
- Preserve explicitly requested Tab shortcuts and document-editing commands such as indentation and table-cell navigation. Keep Ctrl/Command/Alt combinations and IME composition outside the default interception; do not disable controls, blur them, or prevent normal text input to hide focus.

## Personal servers and hosted projects

- Use `server-operations` before working on the user's personal Linux servers (including SSH host `ali`), their hosted projects, or adding another deployment. Explicitly read remote `/opt/AGENTS.md`; SSH does not automatically load remote agent instructions.
- Keep shared server context in `agent-config/skills/server-operations` and project details in each project's `AGENTS.md` and `docs`. After changes, proactively update all affected source configurations and current-state docs, remove obsolete descriptions, and synchronize repository and server copies.
- For shared architecture changes, inspect the entire application inventory and update all affected projects.
- Follow the authorization table in `server-operations` SKILL.md. Documentation edits, commits, pushes and server doc syncs, cleanup of known junk, documented fixes, and fixes to your own mistakes are done without asking and reported afterward. Ask first only for the items that table lists, such as real data or backups, access or permission changes, other apps' downtime, and costs.
