# Media capacity and checkpoint recovery

Use this workflow before reading video screenshots or image batches. Keep the standards for full coverage, discernible detail, and truthful records unchanged, proceeding through more batches within capacity limits.

## Check tokens and bytes separately

- The token window and request-byte ceiling are separate constraints. Image dimensions/detail affect visual tokens, while encoded file size affects request payload. Lower JPEG quality does not necessarily reduce visual tokens, and a larger context window does not raise the request-byte ceiling.
- Images and tool results travel into later requests as history, and automatic compaction may send the entire image history. A small batch, remaining tokens, or previous successful compaction does not prove the next request is safe.
- Inline Base64 is approximately 4/3 of the original file size, plus text, tool definitions, and envelope overhead. Check the actual image copies to be submitted. A file path, image cache, or URL form does not guarantee the server no longer processes the image.
- Request failures have been observed near 100 MiB, but this is not a confirmed universal service limit. The values below are conservative working budgets. Tighten them for lower platform limits; do not raise them merely to pass a check. Do not reuse an old model's capacity figures without current evidence.

## Budget check before loading

Maintain two UTF-8 manifests in this task's temporary workspace, one file path per line: `retained-images.txt` for images loaded into the current context or of uncertain load status, and `next-images.txt` for the next batch. Resolve relative paths against the manifest directory. Register an image again every time it is loaded; do not deduplicate. Start with an empty retained manifest only in a confirmed new context. If resuming an old session whose manifest cannot be reconstructed, hand off first rather than fabricating an empty manifest to continue.

Keep loaded image copies unchanged until that context ends. Save resizing, cropping, or re-encoding as new files; otherwise counting the smaller replacement would underestimate the old payload still in history.

Run this skill's read-only script, replacing `skill-directory` and `temporary-workspace` below with actual paths:

```bash
python3 'skill-directory/scripts/check-media-budget.py' \
  --retained 'temporary-workspace/retained-images.txt' \
  --next 'temporary-workspace/next-images.txt'
```

The script uses only the Python standard library and counts file sizes. It does not open images, call models, or modify manifests. By default, it checks all of the following:

| Check | Default working budget |
|---|---:|
| Images per batch | At most 4; split further if the size limit is exceeded |
| Encoded media payload of the new batch | At most 8 MiB |
| Currently retained images + next batch + non-media reserve | At most 40 MiB |
| Reserve for text, tool definitions, and other overhead | 8 MiB; increase when actual overhead is larger |

JSON `allowed: false` or exit code 1 means the budget disallows loading. Use `violations` to split the next batch or compact/switch context first. Exit code 2 means invalid input; fix the manifests before deciding. Success means only that the static estimate passed, not that the model has seen the images or the service guarantees acceptance.

Also check current token use and limits exposed by the host, reserving visual tokens for the next batch and room for compaction/output. If estimation is unavailable, reduce the batch and hand off early. If request logs show an actual payload larger than the estimate, use the actual value and increase the reserve or lower the working budget. The script neither counts the full conversation nor checks direct audio/video upload limits; separately check those tools' duration, byte, and context constraints.

## Execution order for each batch

1. Select pending frames by continuous scene, preserving necessary boundary overlap. Use navigation copies clear enough to identify layout and original frames or crops to verify detail; do not return a dozen or more large contact sheets in parallel at once. Compression must not impair the text, expressions, or objects being checked.
2. **Budget before loading.** Register this batch's paths in advance; conservatively count uncertain return status in the retained manifest. With parallel tools, combine all images about to return in the same round rather than checking separately and bypassing the total budget.
3. Immediately after observing each batch, write details, source timestamps, and doubts to evidence files, then update coverage and continuation state. Do not wait until a whole ten-minute segment or dozens of contact-sheet pages are viewed. Distinguish generated, returned, and observed-and-saved images, and record audio and visual coverage separately.
4. If the next batch would exceed any budget, or tokens approach the space needed for compaction, complete the handoff below first. Reaching a budget ends only the current media batch; continue the unreviewed scope in a safe context.
5. Keep complete OCR, subtitles, and logs on disk and read by time range or line range. Locate and read truncated portions rather than repeatedly outputting whole files. Retain only project agreements, evidence indexes, the current scene, and necessary prose in the main context.

## Hand off while capacity remains

1. Confirm batch observations are saved, including the last completed range, returned but unorganized range, next task, and audiovisual blind spots. Retain original images, manifests, and indexes needed for unfinished work.
2. Use only compaction or new-context capabilities actually provided by the current host. Confirm capability and authorization before execution; do not invent a `compact` tool. TraeX's `/compact` is an interactive command, not a shell command. Do not change global model or capacity settings on your own.
3. Verify the handoff succeeded through a compaction-complete event, reduced request payload/image count, or a new session confirmed to have loaded only text state. Continue counting any retained images; subtract entries from the retained manifest only when explicitly confirmed removed. Keep uncertain entries conservatively rather than clearing them because a summary was written.
4. Continue after reading the evidence needed for the current segment from saved state. A new context must not inherit the entire media history. If the host lacks a safe handoff capability, save the exact continuation point and explain the missing capability and shortest recovery action rather than adding images until failure. Stop unsafe loading without calling the unfinished task complete.

This skill does not require subagents. If the user or other applicable instructions already permit delegation, use independent media contexts without inherited history, passing only necessary project agreements, source paths, scope, and output locations. Return text observations and indexes without feeding images back into the main context. Each context independently follows the same budgets.

## Recover from oversized content or failed compaction

- For `content is too large`, oversized requests, or similar errors, inspect the failed request's image count, bytes, tokens, and whether it was a compaction request. If there is only `Stream disconnected` without size evidence, diagnose the actual network/service error rather than attributing every failure to payload.
- Stop identical retries. Do not repeatedly continue or compact the same oversized history. If failure occurs before the next model processing step, images already returned by tools cannot automatically count as reviewed.
- Prefer reading the latest saved checkpoint in a new context. Preserve the original task and completion records. Recheck unorganized batches in smaller groups; for completed ranges, revisit only necessary boundaries and doubts rather than repeating all research.
- Smaller batches reduce only new payload. If old images remain in history, first confirm compaction/context switching reduced the load. Deleting disk images, writing summaries, increasing the context window, or editing local manifests cannot remove remote historical payload.
