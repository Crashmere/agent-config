# Global Codex Instructions

## Python environment policy

When a task requires trying, running, testing, or experimenting with Python code:

- Do not install Python packages into the global Python environment unless the user explicitly asks for it.
- Prefer using `uv` to create a separate virtual environment in the relevant project root.
- If the current working directory is inside a project, identify the project root first, usually the Git root.
- Create or reuse a project-local virtual environment such as `.venv`.
- Prefer commands like:
  - `uv venv .venv`
  - `.venv\Scripts\python.exe -m pip install ...`
  - `uv pip install --python .venv\Scripts\python.exe ...`
- Before adding new dependencies, explain why they are needed.
- If a dependency is only needed for a temporary experiment, avoid modifying project dependency files unless explicitly requested.
- Do not use `pip install --user` or global `pip install` unless the user explicitly authorizes it.

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

When the user asks to install software:

- Compare the reasonable installation methods for the user's operating system and the specific software before taking action.
- On Windows, consider common options such as `winget`, `scoop`, and official installer scripts or downloads.
- On macOS, consider Homebrew and any official installer path that is more appropriate for the software.
- Match the installation method to the software's characteristics.
- Prefer `scoop` when the software is command-line focused, portable, or easy to manage as a self-contained package.
- Prefer `winget` or an official installer when the software has a substantial GUI, installs drivers or services, integrates deeply with the system, or is better maintained by the vendor installer.
- Consider update and maintenance behavior before recommending an installation method.
- Account for software that self-updates, such as browsers or game platforms, because package managers may not always stay synchronized with the application's own updater.
- Present the tradeoffs and a recommendation, then wait for the user's final decision before executing the installation.

## General workflow

- Prefer safe, project-local changes.
- Do not modify unrelated files.
- Before running destructive commands, explain the command and ask for confirmation.
