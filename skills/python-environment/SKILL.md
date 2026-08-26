---
name: python-environment
description: Manage isolated Python environments and dependencies safely. Use whenever a task requires running or testing Python code with third-party packages, creating or selecting a virtual environment, installing or changing Python dependencies, choosing among uv, pip, Poetry, or other project tooling, or troubleshooting interpreter, package, import, native extension, DLL, or Windows Python security-blocking issues.
---

# Python Environment

## Workflow

1. Find the project root, normally the nearest Git root, before creating an environment or installing packages.
2. Inspect the project for an existing environment and dependency workflow, including `.venv`, `pyproject.toml`, `uv.lock`, `requirements*.txt`, `poetry.lock`, `Pipfile`, Conda files, and documented project commands.
3. Reuse the project's established tool and environment when they are healthy. Do not migrate dependency managers as a side effect of another task.
4. If no workflow exists, prefer `uv` and a project-local `.venv`. Never install into the global Python environment unless the user explicitly requests it.
5. When the network location can benefit from a nearby mirror, or the default package index is slow or unreliable, prefer a trusted mirror such as Tsinghua TUNA for ordinary PyPI packages. Scope the override to the current command or task unless the user requests persistent configuration.
6. Decide whether a dependency is part of the project or only needed for a temporary experiment. Update project dependency files only when the dependency belongs to the project or the user requests it.
7. Run Python and package commands through the selected environment explicitly.
8. Verify the interpreter path, required imports, and the command or test that motivated the environment change.

On Windows, read [references/windows-native-imports.md](references/windows-native-imports.md) when a package is installed but importing a `.pyd` or dependent DLL fails, or when the error may come from ABI, architecture, native runtime, Mark-of-the-Web, application control, or antivirus enforcement. Diagnose the class of failure before reinstalling the package.

Read [references/package-indexes.md](references/package-indexes.md) when selecting or troubleshooting a mirror, private index, or framework-specific package source.

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
- Do not replace project-declared, private, authenticated, or framework-specific indexes with a general PyPI mirror. Use official PyTorch accelerator indexes and other vendor-required sources when compatibility depends on them.
- If a mirror lacks a package, serves stale metadata, fails integrity checks, or causes resolution differences, retry the same operation against the project's original or official source before changing versions or constraints.
- Use HTTPS mirrors and retain package hash and signature verification. Never bypass TLS or trusted-host checks merely to improve download speed.
- Report the environment used and the verification result.
