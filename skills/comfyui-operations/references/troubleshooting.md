# ComfyUI troubleshooting

## Start with the failure class

```text
Request rejected
├── missing node or invalid input
├── missing model
└── invalid workflow/API conversion

Execution fails
├── Python/native dependency failure
├── CUDA, MPS, ROCm, DirectML, or CPU backend problem
├── out of memory
└── corrupt or incomplete model

Execution succeeds but image is wrong
├── model-family and graph mismatch
├── wrong VAE or text encoder
├── unsuitable sampler parameters
├── prompt-conditioning issue
└── stale or corrupted process/GPU state

Image fails to load
├── output was deleted
├── cached execution returned an old filename
├── wrong output type/subfolder
└── `/view` returns 404
```

## Compare artifacts, not recollections

ComfyUI PNG files commonly embed `prompt` and `workflow` JSON. Extract metadata from the last known-good and first bad outputs, then compare exact values and links. Check at least:

- checkpoint name and model family;
- latent node type, width, height, and batch size;
- model patches or alternate sampling nodes;
- positive and negative CLIP sources;
- VAE source;
- seed and seed-control mode;
- steps, CFG, sampler, scheduler, and denoise;
- custom nodes and their versions.

Do not assume a saved workflow matches the graph embedded in an earlier image.

## Noise or mosaic output

Treat dense color noise or mosaic output as generated corruption, not a file-format problem, when the PNG opens correctly and has normal dimensions.

1. Check architecture first. For example, an SDXL/Pony checkpoint requires an SDXL-compatible graph. An SD3 latent node or an unrelated model-sampling patch can complete without a useful image.
2. Replay the known-good embedded API prompt with the same seed and parameters. Change only the filename prefix initially.
3. If the result is cached or points to a deleted file, change the seed to force actual sampling.
4. Replace prompts with concise neutral controls only after graph equivalence is established. If both ordinary and suspect prompts fail, prompt content is not the root cause.
5. Restart ComfyUI and repeat with a fresh seed. If this restores correct images, inspect model/GPU memory state rather than rewriting the workflow.
6. When repeated runs later corrupt output, test conservative startup flags supported by that ComfyUI version. On a CUDA system, relevant diagnostic flags may include:

   ```text
   --disable-dynamic-vram
   --disable-async-offload
   --disable-cuda-malloc
   --disable-pinned-memory
   ```

   Change the smallest plausible set. These are compatibility fallbacks, not universal defaults. Validate with several consecutive images and alternating prompt inputs before persisting them.

## Deleted output and stale cache

Deleting a PNG from `output/` does not clear ComfyUI's in-memory node cache. With a fixed seed and unchanged inputs, a new queue request may finish in `0.00` seconds, mark all nodes in `execution_cached`, and return the deleted filename. The frontend then requests `/view` and receives 404.

Confirm all of these:

- `/history/<prompt_id>` reports success;
- `execution_cached` includes the sampler and save path;
- the returned output filename no longer exists;
- `/view?filename=...&type=output` returns 404.

Force a fresh run by changing the seed or another true upstream input. Use `randomize` for unrelated images or `increment` for reproducible sequences. Restart the service when the exact fixed seed and graph must be recomputed after its output was deleted.

## Model files

- Compare source and destination byte lengths after large transfers. Use SHA-256 when corruption is suspected.
- Inspect safetensors headers without loading full tensors when possible. Confirm the checkpoint contains the expected model, CLIP, and VAE components.
- Distinguish a checkpoint from LoRA, VAE, ControlNet, text encoder, diffusion model, and upscaler files; place each in its corresponding directory.
- Do not create a hard link when the requested outcome is a real move with no remaining source entry. Verify the final link count or file identity if hard-link behavior is in doubt.

## Logs and successful-looking failures

A completed progress bar proves that the sampler ran, not that the image is semantically valid. Collect:

- startup device, dtype, attention, and memory-management lines;
- model, CLIP, and VAE load lines;
- warnings about NaN, OOM, allocation, offload, or unsupported operations;
- execution duration and cached-node list;
- the actual output image and embedded metadata.

Always inspect representative images after a stability test.
