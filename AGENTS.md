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
