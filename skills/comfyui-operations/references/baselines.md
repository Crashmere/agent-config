# Known-good baselines

Create a baseline after the first visually correct end-to-end generation and before upgrades or risky configuration changes. Use it to distinguish installation/runtime regressions from changes in a user's active workflow.

## Baseline contents

Store a small machine-local baseline bundle outside the skill repository:

```text
comfyui-baseline/
├── prompt.json
├── output.png
├── environment.json
└── model.json
```

- `prompt.json`: the exact API-format prompt that produced the accepted image, including graph links, seed, dimensions, sampler, scheduler, steps, CFG, denoise, and filename prefix. Prefer a concise neutral prompt and built-in nodes.
- `output.png`: one visually inspected reference output with intact ComfyUI metadata. It is evidence, not a pixel-equality oracle across all backend versions.
- `environment.json`: ComfyUI revision/version, frontend and custom-node revisions, startup arguments, OS/architecture, accelerator device/backend, and the interpreter/PyTorch summary supplied by `$python-environment`.
- `model.json`: model type, relative ComfyUI path, byte length, and SHA-256 when practical. Do not copy the full checkpoint into the baseline bundle.

Keep credentials, host secrets, private prompts, and unrelated generated images out of the bundle. Preserve model license or provenance separately when required.

## Establish the baseline

1. Use a minimal workflow that covers checkpoint loading, CLIP encoding, latent creation, sampling, VAE decoding, and image saving. Avoid optional custom nodes unless they are part of the capability being accepted.
2. Submit it through `scripts/run_prompt.py --require-execution`. A successful HTTP response or saved image is insufficient if the critical generation nodes were cached.
3. Confirm the expected accelerator and model in the server logs and `/system_stats`.
4. Open the output and inspect it visually for semantic structure, not merely valid PNG dimensions.
5. Copy the exact submitted API prompt and accepted PNG into the bundle. Record the environment and model facts without embedding machine credentials.
6. Run `scripts/inspect_workflow.py` on the saved prompt and PNG to confirm that their embedded graph and parameters are readable.

## Replay the baseline

1. Preserve the stored baseline files unchanged. Make a working copy of `prompt.json`.
2. Change only the output prefix for an exact replay. If the returned output is stale or the generation nodes are cached, change the seed in the working copy to force sampling; record that controlled difference.
3. Run the working copy with `scripts/run_prompt.py --require-execution` and download the output.
4. Compare logs, execution evidence, graph, model, parameters, and the actual image with the baseline. Do not require pixel identity after hardware, backend, or dependency changes unless determinism for that exact stack has been established.
5. If the baseline fails, treat the installation, model, backend, process state, or shared graph as suspect before modifying the user's active workflow or blaming prompt content.

## Refresh rules

- Keep the old baseline while evaluating an upgrade. Create a new versioned baseline only after the new stack passes foreground startup, real execution, visual inspection, and repeated-run stability checks.
- Do not silently overwrite a baseline because a failed run produced a new file with the same name.
- Rebuild platform-specific environment data when moving between Windows, macOS, and Linux. Reuse portable workflow/model facts only after compatibility is confirmed.
