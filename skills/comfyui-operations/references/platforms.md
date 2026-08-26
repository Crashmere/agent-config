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
- For a manual source installation, prefer the latest stable ComfyUI release tag over an untagged `master` commit unless the user requests development builds. Use a project-local Python 3.12 environment by default when the current ComfyUI metadata permits it; it is a conservative compatibility choice for custom nodes. Install the checked-out release's own dependency declaration rather than copying a stale package list.
- On Apple Silicon, verify both `torch.backends.mps.is_available()` and an actual tensor operation on `device="mps"`. Then confirm `Device: mps` in startup logs and `type: mps` from `/system_stats`; package import alone is insufficient. CUDA, ROCm, Triton, and `comfy-aimdo` unavailable messages are expected when the selected device is MPS unless they prevent startup.
- Start locally on `127.0.0.1` unless LAN access is explicitly needed.
- Allow extra time for the first startup. Native libraries, node modules, frontend assets, and initial database migrations may delay the listener after the MPS device line appears. Keep observing the live process and logs; do not classify the installation as failed solely because port `8188` is not listening immediately.
- For an interactive local launcher, prefer a `.command` script that keeps Terminal attached, writes logs, polls `/system_stats`, and opens the browser only after readiness. A child launched with `nohup ... &` from an agent or automation shell may still be reaped when that host command exits even after a successful readiness check. Use `scripts/install_macos_launchers.sh <comfy-root>` to install the maintained launcher pair when appropriate.
- A stop launcher must resolve the actual listener PID, verify both its current working directory and `main.py` command, and only then signal it. A wrapper-shell PID is not necessarily the Python listener PID, especially when output is piped through `tee`.
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
5. The expected checkpoint appears in the object/model list. If no model is installed, record this as not tested rather than interpreting default-workflow validation errors as a server failure.
6. A minimal workflow generates and saves a visually valid image. This remains unverified when model provisioning is outside the requested scope.
