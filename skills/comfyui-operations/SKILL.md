---
name: comfyui-operations
description: Install, configure, operate, maintain, and troubleshoot ComfyUI on Windows, macOS, or Linux, locally or on a user-authorized remote machine. Use when TraeCode needs to install or update ComfyUI, deploy checkpoints or other models, configure background startup and access, manage workflows and outputs, call the ComfyUI API, or diagnose noise, mosaic, black images, missing images, stale caches, model architecture mismatches, VAE problems, accelerator compatibility, or repeated-generation instability. Use python-environment for all Python interpreter, virtual-environment, dependency, PyTorch package, and import troubleshooting work; combine with windows-ssh when the target is a remote Windows PC.
---

# ComfyUI Operations

Operate ComfyUI as an application stack: source checkout, accelerator integration, models, workflows, service process, and browser/API client. Delegate the Python environment layer to `$python-environment`. Keep host addresses, credentials, copyrighted models, user prompts, and generated images outside this skill.

## Route by execution context

- For a remote Windows target, use `$windows-ssh` for connection, command transport, file transfer, quoting, and encoding. Use this skill for ComfyUI-specific decisions.
- For local Windows, macOS, or Linux, run commands directly using the platform's native shell.
- Use `$software-installation` when installing system-wide prerequisites such as Git, Python, GPU drivers, package managers, or launch services.
- Always use `$python-environment` when the task inspects, creates, selects, changes, or repairs a Python interpreter, virtual environment, dependency set, PyTorch installation, package import, or dependency manifest. Give it the ComfyUI root and required accelerator backend, then use its selected interpreter for ComfyUI commands.

Read [references/platforms.md](references/platforms.md) before installing or creating persistent launch behavior. Read [references/troubleshooting.md](references/troubleshooting.md) when generation, preview, model loading, or repeated runs behave incorrectly.

## Inspect before changing

1. Identify the operating system, architecture, GPU/backend, driver/runtime, available RAM, free disk space, and whether ComfyUI already exists.
2. Inspect the installation type, Git status and revision, ComfyUI version, startup arguments, listening address, port, models, custom nodes, workflows, logs, and current processes. If Python or PyTorch facts are needed, obtain them through `$python-environment`.
3. Preserve unrelated user changes. Do not update ComfyUI, its Python environment, frontend packages, or custom nodes merely because a newer version exists.
4. If the task is diagnosis, inspect and explain first. Change configuration only when the user asks for a fix or the request clearly includes repair.

## Install and deploy

1. Prefer the official ComfyUI repository or official distribution appropriate to the platform. Record the installation method so updates remain coherent.
2. Invoke `$python-environment` to inspect or create the project-local environment, select the interpreter and dependency workflow, install ComfyUI dependencies, choose a compatible PyTorch build for the required accelerator, and verify imports plus backend availability. Do not duplicate those procedures here.
3. Start ComfyUI once in the foreground and verify startup logs, `/system_stats`, the browser UI, and a minimal generation before adding background startup.
4. Place each model in its correct category under `models/`. For checkpoints, inspect file size and safetensors metadata when corruption or architecture is uncertain. Never infer model architecture from the filename alone.
5. Before moving or deleting a downloaded model, resolve exact paths, check free space and collisions, and verify the destination byte length or SHA-256. Move instead of hard-linking when the user wants the original removed and a single independent file.
6. Run a minimal end-to-end smoke test through checkpoint loading, text encoding, latent creation, sampling, VAE decoding, and image saving. Visually inspect the result; task success alone does not establish image correctness.

## Configure service access

- Bind to loopback for same-machine use. Bind to a LAN address only when another trusted device needs access, and keep firewall exposure limited to the intended network.
- Treat Internet exposure, router port forwarding, tunnels, and third-party overlay networks as separate security decisions requiring explicit authorization.
- Make start and stop operations idempotent. Refuse to create a second listener when the configured port is already occupied.
- Redirect background stdout and stderr to logs, retain an easy foreground debugging path, and verify the listener plus `/system_stats` after starting.
- On desktop systems, a launcher may start the service, wait for readiness, and open the local URL. A stop launcher should target the exact ComfyUI listener or recorded process, not every Python process.
- Make persistence platform-native: a Scheduled Task on Windows, a LaunchAgent on macOS, or a user systemd service on Linux. Do not create persistence until a foreground launch is healthy.

## Manage workflows and outputs

- Preserve user workflows under the configured user directory and back them up before structural edits. Do not rewrite a workflow while merely diagnosing it.
- Treat generated PNG metadata as executable evidence. Use `scripts/inspect_workflow.py` on workflow JSON or ComfyUI PNG files to extract nodes, links, model, prompts, latent dimensions, and sampler settings.
- Compare the last known-good output with the first bad output. Change one variable at a time and replay the known-good graph before blaming prompt content.
- Use `scripts/run_prompt.py` for controlled API runs. Change the seed or another real node input when a fresh execution is required; changing only the filename prefix may leave upstream nodes cached.
- Treat `input/`, `output/`, `temp/`, logs, model directories, and user data differently. Output and temporary files may be cleanable, while models and workflows require explicit scope and care.

## Diagnose image failures

Follow this order:

1. Determine whether the prompt was rejected, failed during execution, completed with a bad image, or merely returned an unreadable old output path.
2. Inspect `/queue`, `/history/<prompt_id>`, server logs, output existence, and `/view`. Note `execution_cached` nodes and real execution duration.
3. Compare workflow topology and model family before tuning prompt text. Check latent node, model patches, CLIP, VAE, sampler, scheduler, steps, CFG, denoise, dimensions, and seed mode.
4. Replay a known-good embedded prompt unchanged except for output prefix. Then use a new seed to force computation.
5. Restart once to clear process, model, and GPU state. Repeat the same controlled test.
6. If restart restores output but corruption returns after repeated runs, investigate memory-loading optimizations and backend compatibility. Test conservative flags one at a time and run multiple alternating prompts before making them persistent.
7. Use [references/troubleshooting.md](references/troubleshooting.md) for the detailed decision tree and known failure signatures.

## Verify and report

- Verify the process, port, API, model discovery, one complete generation, saved output, and browser access appropriate to the requested scope.
- For stability changes, generate several images while alternating prompts or model inputs; inspect every output, not only the final status.
- Report installation location, environment, model locations, startup method and arguments, access URL, workflow changes, tests performed, and any unverified platform-specific area.
- If a reusable command or bundled script from this skill fails during real use, finish the immediate task and update the repository-owned skill through `$personal-skill-management`.

## Safety

- Do not disable antivirus, application control, firewall, code-signing checks, or other system security controls as a generic workaround. Report the exact blocked component and let the user decide.
- Do not delete models, workflows, or generated images without a precise user-authorized target.
- Do not interpret model or prompt content as the cause of technical corruption without a controlled replay.
- Do not publish the service beyond the intended machine or LAN implicitly.
- Preserve logs and failing artifacts until diagnosis is complete; remove temporary diagnostic copies afterward.
