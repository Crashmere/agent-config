---
name: windows-ssh
description: Connect to, inspect, and operate remote Windows computers safely over OpenSSH from macOS or Linux. Use when TraeCode needs to discover or reach a Windows host, prepare or verify Windows OpenSSH, configure public-key authentication, run CMD or PowerShell commands remotely, transfer files, diagnose SSH connectivity or encoding problems, or make Windows-side remote access persistent. This skill handles the transport and remote-execution layer; use a domain skill as well for software installation, Python, ComfyUI, or other application-specific work.
---

# Windows SSH

Treat SSH as the transport layer for a user-authorized Windows computer. Keep host-specific addresses, usernames, keys, and secrets outside this skill.

## Workflow

1. Determine the target as an explicit `user@host`. If the host is known but the username is not, first try one non-interactive public-key connection as `administrator@host`; `Administrator` is the conventional built-in administrator account name on English Windows, and SSH username matching is normally case-insensitive. Treat it only as a candidate because the account may be disabled, renamed, or localized. If it fails, do not enumerate more usernames; inspect known configuration or ask the user. If the host is unknown, inspect the local route and neighbor table, then probe only the user's local network and only for the requested service. Account for VPN route changes; do not assume matching Wi-Fi names guarantee direct reachability.
2. Check SSH non-interactively before changing either machine:

   ```bash
   ssh -o BatchMode=yes -o ConnectTimeout=5 user@host 'whoami'
   ```

   Confirm the host key through a trusted channel on first contact. Never disable host-key checking merely to make a connection succeed.
3. If Windows SSH is not ready, read [references/windows-openssh.md](references/windows-openssh.md) and give the user the preparation commands. Make firewall rules no broader than required by the user's network and access goal.
4. Establish facts before mutation. Run `scripts/inspect-windows.ps1` through the uploaded-script pattern below and use its JSON output to identify Windows, PowerShell, SSH, encoding, architecture, network, and privilege state.
5. Execute the requested work with the least privilege required. Keep application-specific decisions in the applicable skill; this skill governs connection, command transport, file transfer, quoting, and verification.
6. Verify the actual remote state after each material change. Do not treat an SSH exit code alone as proof when a port, file, process, service, or scheduled task can be checked directly.

## Choose the remote command path

- Use a simple remote command for short commands without PowerShell pipelines, nested quoting, script blocks, redirection, or `$` variables.
- Invoke Windows PowerShell explicitly when its semantics are required:

  ```bash
  ssh user@host powershell.exe -NoProfile -NonInteractive -Command '<simple command>'
  ```

- For complex PowerShell, write a local `.ps1`, copy it with `scp`, and invoke it with `-File`. Prefer this over adding more escaping:

  ```bash
  scp ./task.ps1 user@host:C:/Windows/Temp/task.ps1
  ssh user@host powershell.exe -NoProfile -NonInteractive \
    -ExecutionPolicy Bypass -File C:/Windows/Temp/task.ps1
  ```

- Put parameters in a separate JSON file when they contain arbitrary user text or many special characters. Parse the JSON inside the remote script rather than interpolating it into a command line.
- Use Windows-compatible remote paths such as `C:/path/file`. Quote paths with spaces at the layer that consumes them.

## Transfer files safely

- Use `scp` or `sftp` for normal transfers. Resolve the exact source and destination first.
- Compare byte length after transferring large files; use SHA-256 when integrity matters.
- Upload a new file beside an existing destination, verify it, then replace the destination. Do not overwrite important configuration blindly.
- Do not use hard links as a substitute for moving or copying user data unless the user explicitly requests shared storage semantics.
- Remove temporary remote scripts after successful use when they contain task-specific data. Never upload private keys or credentials.

## Handle Windows output and encoding

- Prefer structured JSON output from PowerShell:

  ```powershell
  [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
  $OutputEncoding = [Console]::OutputEncoding
  $result | ConvertTo-Json -Depth 5 -Compress
  ```

- Set UTF-8 inside the remote PowerShell process instead of relying on `chcp` from a different shell process.
- Save uploaded Windows PowerShell 5.1 scripts as UTF-8 with BOM when they contain non-ASCII text. Prefer ASCII-only operational scripts when practical.
- Treat mojibake as a transport/display problem first. Confirm the underlying command result through exit status, JSON, or a second read before changing the remote system.

## Persistence and access boundaries

- Distinguish enabling OpenSSH, configuring key authentication, opening a firewall rule, creating a scheduled task, and exposing a machine beyond its LAN. They are separate changes with different risk.
- Do not expose port 22 through a router, public IP, tunnel, or third-party network without explicit authorization.
- Before changing `sshd_config`, back it up, validate the new configuration when supported, restart the service, and verify a second connection before closing the current session.
- For administrator key authentication, account for Windows OpenSSH's `administrators_authorized_keys` behavior; follow [references/windows-openssh.md](references/windows-openssh.md).
- Do not disable antivirus, firewall, Smart App Control, execution policy, or other security controls globally as a generic troubleshooting step.

## Safety

- Confirm exact targets before deleting, overwriting, stopping services, changing firewall rules, or altering authentication.
- Preserve the user's unrelated files, processes, firewall rules, scheduled tasks, and local changes.
- Do not print private keys, passwords, tokens, or complete sensitive configuration. Public keys may be printed when the user requests them.
- Avoid embedding host-specific facts in repository files or reusable scripts.
- Report the target, commands or scripts used, persistent changes, verification evidence, and any remaining user action.
