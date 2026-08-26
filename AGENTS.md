# Global Agent Instructions

## Python environment policy

- Never install Python packages into the global environment unless the user explicitly requests it.
- Use the `python-environment` skill whenever Python execution requires third-party packages, environment creation or selection, dependency changes, or interpreter/package troubleshooting.

## Instruction management

When the user asks to add, update, or reorganize global agent instructions:

- First consider whether the requested behavior belongs in `AGENTS.md` or should be implemented as a skill.
- Prefer `AGENTS.md` for always-on behavioral policies, safety rules, workflow preferences, environment constraints, and broad collaboration norms.
- Prefer a skill for specialized, task-specific workflows, reusable domain procedures, tool integrations, templates, or instructions that should only be loaded when relevant.
- Briefly explain the placement decision before editing.
- Before adding new content to `AGENTS.md`, consider how it fits with the existing instructions.
- If the requested change conflicts with existing instructions, stop and ask the user how to resolve the conflict before editing.
- When appropriate, update nearby existing wording so the file stays coherent rather than simply appending disconnected rules.

## Software installation policy

- Prefer official or first-party software sources.
- Use the `software-installation` skill for software installation, upgrade, removal, or installation troubleshooting.
- When the user explicitly requests installation, complete it and verify the result unless a material risk or unresolved choice requires confirmation.

## General workflow

- Keep changes safe, scoped, and relevant to the task.
- Explain destructive actions and ask for confirmation before running them.
