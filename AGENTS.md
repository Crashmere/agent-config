# Global Agent Instructions

## Python environment policy

- Never install Python packages into the global environment unless the user explicitly requests it.
- Use the `python-environment` skill whenever Python execution requires third-party packages, environment creation or selection, dependency changes, or interpreter/package troubleshooting.

## Instruction management

- Use the `personal-skill-management` skill when organizing agent instructions or creating and maintaining the user's own skills and their `agent-config` GitHub repository.

## Software installation policy

- Prefer official or first-party software sources.
- Use the `software-installation` skill for software installation, upgrade, removal, or installation troubleshooting.
- When the user explicitly requests installation, complete it and verify the result unless a material risk or unresolved choice requires confirmation.

## General workflow

- Keep changes safe, scoped, and relevant to the task.
- Explain destructive actions and ask for confirmation before running them.
