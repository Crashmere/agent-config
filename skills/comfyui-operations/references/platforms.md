# Platform notes

## Common installation shape

Keep these concepts stable across platforms:

```text
<comfy-root>/
├── .venv/
├── models/
├── user/
├── input/
├── output/
├── temp/
└── logs/
```

The source tree is replaceable; models, user workflows/settings, and selected outputs are user data. Keep launch configuration outside tracked upstream files when practical. Use `$python-environment` for every interpreter, `.venv`, dependency, PyTorch package, and import decision described by an installation task.

## Windows

- Use `$windows-ssh` in addition to this skill when operating remotely.
- Prefer forward-slash paths in remote command arguments, for example `C:/AI/ComfyUI`, to reduce escaping problems.
- Use the interpreter selected by `$python-environment` explicitly in launchers and scheduled tasks; do not depend on PATH.
- Test in the foreground before creating a Scheduled Task. A background launcher should use `Start-Process`, a specific working directory, hidden window style, and separate stdout/stderr logs.
- A desktop shortcut may invoke a wrapper that starts the service, polls `/system_stats`, and opens the URL. Keep a separate stop shortcut that resolves the listener on the configured port.
- For complex setup or launcher creation, upload a `.ps1` and run it with `powershell.exe -File`; do not fight nested SSH/CMD/PowerShell quoting.
- Save Windows PowerShell 5.1 scripts with a UTF-8 BOM if they contain non-ASCII text. Prefer JSON output for inspection commands.

## macOS

- Identify Apple Silicon versus Intel and require an appropriate Metal/MPS or CPU backend. Delegate Python and PyTorch selection plus backend verification to `$python-environment`. Do not apply CUDA-specific flags.
- Start locally on `127.0.0.1` unless LAN access is explicitly needed.
- Use a per-user LaunchAgent only after foreground execution and generation succeed. Set `WorkingDirectory`, explicit interpreter and script paths, log paths, and restart behavior deliberately.
- Account for LaunchAgent's minimal environment: do not depend on interactive shell PATH or startup files.

## Linux

- Identify whether ComfyUI should use NVIDIA, AMD/ROCm, Intel, or CPU. Delegate compatible PyTorch selection, installation, and backend verification to `$python-environment`.
- Prefer a user-level systemd service for persistence. Set an explicit working directory, interpreter, arguments, restart policy, and logs.
- Avoid running ComfyUI as root. Bind and firewall the port according to the actual access scope.

## Portable verification

After installation or startup, verify:

1. The interpreter selected and verified through `$python-environment` starts ComfyUI.
2. Startup logs show the expected backend and device.
3. The configured host and port listen.
4. `GET /system_stats` succeeds.
5. The expected checkpoint appears in the object/model list.
6. A minimal workflow generates and saves a visually valid image.
