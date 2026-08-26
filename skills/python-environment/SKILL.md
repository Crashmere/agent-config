---
name: python-environment
description: Manage isolated Python environments and dependencies safely. Use whenever a task requires running or testing Python code with third-party packages, creating or selecting a virtual environment, installing or changing Python dependencies, choosing among uv, pip, Poetry, or other project tooling, or troubleshooting interpreter and package issues.
---

# Python Environment

## Workflow

1. Find the project root, normally the nearest Git root, before creating an environment or installing packages.
2. Inspect the project for an existing environment and dependency workflow, including `.venv`, `pyproject.toml`, `uv.lock`, `requirements*.txt`, `poetry.lock`, `Pipfile`, Conda files, and documented project commands.
3. Reuse the project's established tool and environment when they are healthy. Do not migrate dependency managers as a side effect of another task.
4. If no workflow exists, prefer `uv` and a project-local `.venv`. Never install into the global Python environment unless the user explicitly requests it.
5. Decide whether a dependency is part of the project or only needed for a temporary experiment. Update project dependency files only when the dependency belongs to the project or the user requests it.
6. Run Python and package commands through the selected environment explicitly.
7. Verify the interpreter path, required imports, and the command or test that motivated the environment change.

## Default commands

For a new macOS or Linux environment:

```bash
uv venv .venv
uv pip install --python .venv/bin/python <package>
.venv/bin/python <script>
```

For a new Windows environment:

```powershell
uv venv .venv
uv pip install --python .venv\Scripts\python.exe <package>
.venv\Scripts\python.exe <script>
```

When the project has a `uv.lock`, prefer `uv sync` and `uv run`. When it declares another manager, use that manager's documented workflow.

## Guardrails

- Explain why a new dependency is needed before installing it.
- Avoid `pip install --user`, global `pip install`, and `sudo pip`.
- Do not delete or recreate a working environment merely to make it conform to a preferred tool.
- Do not modify lockfiles or dependency manifests for one-off diagnostics unless necessary and authorized.
- Report the environment used and the verification result.
