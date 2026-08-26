---
name: software-installation
description: Choose, install, upgrade, remove, and troubleshoot software using an appropriate trusted distribution channel. Use when the user asks to install or update a CLI, desktop application, package manager, runtime, system component, or developer tool; compare installation methods; resolve PATH or duplicate-installation problems; or verify an installation.
---

# Software Installation

## Workflow

1. Identify the operating system, architecture, shell, and whether the software is already installed. Check how an existing copy was installed before changing it.
2. Check project or workspace instructions and prefer an existing project-local toolchain when the software is a development dependency.
3. Compare reasonable channels by source trust, platform integration, update behavior, version availability, reversibility, and conflicts with existing installations.
4. Prefer the official or first-party source. Use a well-maintained platform package manager when it provides the official or clearly supported package.
5. If the user explicitly requested installation or upgrade, proceed without asking them to repeat the decision. Ask only when an unresolved choice materially changes the result or the action introduces significant risk.
6. Install with the narrowest privileges required. Do not use elevated privileges merely for convenience.
7. Verify the installed binary or application, version, PATH resolution, and any health check that the software provides. Report the selected method and result.

## Method selection

- On macOS, consider Homebrew, the Mac App Store, and the vendor's signed installer. Prefer Homebrew for well-maintained CLI packages; prefer the vendor channel when it owns updates or requires deeper system integration.
- On Windows, consider Winget, Scoop, and the vendor installer. Prefer Scoop for portable CLI tools; prefer Winget or the vendor installer for substantial GUI applications, drivers, and services.
- On Linux, follow the distribution's package manager when versions are suitable; otherwise use the vendor's documented repository or installer.
- For language-specific developer tools, prefer a project-local installation when practical. Use a global installation only when the tool is intentionally machine-wide.

## Confirmation boundaries

Pause for confirmation before:

- installing drivers, kernel extensions, system services, or security-sensitive components;
- replacing or removing a working installation managed by a different channel;
- accepting licenses, paid plans, or account-level changes the user has not already authorized;
- making a choice between materially different editions, versions, or installation scopes;
- performing destructive cleanup or removing user data.

Do not pause merely because a normal installation writes outside the current project when that is inherent to the user's explicit request.
