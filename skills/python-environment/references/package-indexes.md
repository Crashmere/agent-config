# Python package indexes

Use a mirror to improve availability and download speed without changing the dependency graph or weakening verification. Inspect the project's existing index configuration first and preserve it when it is deliberate.

## Temporary PyPI mirror

Prefer a per-command override. For users in mainland China, try the HTTPS Tsinghua TUNA PyPI mirror first:

```bash
uv pip install --default-index https://pypi.tuna.tsinghua.edu.cn/simple <package>
pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple <package>
```

Apply the same `uv` option to `uv sync` or `uv run` when that command performs dependency resolution. If the installed `uv` version does not recognize `--default-index`, inspect `uv <command> --help` and use its documented index option rather than guessing.

For a task containing several commands, use a task-scoped environment variable instead of repeating the URL, then unset it or keep it local to the subprocess:

```bash
UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple uv sync
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple pip install <package>
```

Do not write a persistent global `pip`, `uv`, Poetry, or Conda configuration unless the user asks for it. If persistence is requested, inspect existing configuration, explain the scope, preserve authenticated or private sources, and verify the resulting effective configuration.

## Source selection

- Use a general PyPI mirror only for packages normally resolved from PyPI.
- Preserve project-declared indexes and private repositories. Do not expose credentials in commands or logs.
- Use the official PyTorch index or the project's documented source for CUDA, ROCm, CPU, or other accelerator-specific wheels; a general mirror may not carry the required build.
- Follow vendor instructions for packages distributed through custom indexes or direct URLs.
- Keep Git, local-path, and direct-URL dependencies on their declared sources.
- Treat Conda channels separately from PyPI indexes and preserve the project's channel order and strictness.

## Fallback and verification

If the mirror times out, lacks a release, returns stale metadata, changes resolution, or fails a hash check, retry against the original or official index before altering dependency constraints. After installation, verify the selected interpreter, resolved package version and origin when relevant, imports, and the task that required the package.
