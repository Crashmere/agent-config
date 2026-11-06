# Media workflows and delivery

Use this reference for video/audio graphs, image conditioning, and multi-shot production. Discover the installed nodes and provider schemas as described in [cli.md](cli.md); the named examples below are not fixed model recommendations.

## Image editing and conditioning

- ControlNet preprocessing produces an image representation; it does not produce the CONTROL_NET model. Match the preprocessor and model, then supply image, CONTROL_NET, and conditioning to the appropriate apply node.
- For `ImageCompositeMasked`, the mask matches the source image's dimensions, not an arbitrary destination canvas. Check each mask-consuming node's semantics instead of assuming that all masks use the same size or polarity.
- A replacement/fill API is not necessarily a low-denoise refinement API. Inspect whether strength/denoise exists before selecting it for an edit that must preserve the original.
- Local model-based upscaling commonly uses `LoadImage` -> `UpscaleModelLoader` -> `ImageUpscaleWithModel` -> `SaveImage`. Verify actual model choices and preserve metadata when it is needed for replay.

## Video and audio graphs

A node returning VIDEO is not automatically an output node. Connect it to a suitable terminal save node, such as `SaveVideo`, so a job exposes a downloadable artifact. For assembly, current core examples use `GetVideoComponents`, `BatchImagesNode`, `CreateVideo`, and `SaveVideo`; follow the installed schemas and autogrow input names.

Carry the actual frame rate from the video-components output into assembly. Discover its slot rather than assuming an output index across versions. Provider clips may have off-spec dimensions, duration, or frame rate; measure them before concatenating or matching an exact runtime:

```bash
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate,duration -of json clip.mp4
```

Text-to-video and image-to-video variants can share a model selector. Validate the chosen variant's required image/start/end-frame inputs before paying for a run. Motion prompts should express movement, camera behavior, and timing as well as the scene content.

For talking heads, feed the exact audio used in the final mix to the lip-sync node. Compare audio and video durations: trailing still frames can accumulate timing drift across clips. Trim or retime each shot before conforming, using an intentional pause rather than blindly concatenating padded outputs.

Audio duration in text encoding and latent construction must agree for models that require both. Follow live enum values rather than a familiar notation: an ACE-Step workflow can require timesignature `"4"`, not `"4/4"`. Instrumental mode and conditioning wiring are model-specific; inspect a working template instead of transferring settings from another family.

The reviewed cloud material reports that uploaded audio/video may not appear in `LoadAudio`/`LoadVideo` choices even when uploaded images appear in `LoadImage`. Check the current target choices before choosing an upload-to-loader handoff. In-graph generated audio, IMAGE, or VIDEO connections avoid that catalog dependency; local assembly is an alternative when a review boundary requires separate files.

## Multi-shot production

Establish the concept, causal beats, timings, and continuity plan before committing to expensive multi-shot renders. A shot list should explain what changes at each cut and how the audience recognizes the same people and locations. Preserve an explicitly requested technique or style; do not replace the brief with a preferred production method.

Use a canonical character/location reference, reference-based reframing, or the previous shot's selected end frame when continuity matters. Reuse wardrobe, lighting, voice parameters, and framing constraints deliberately. Approve the hero still and voice candidate before propagating them into many paid shots.

Keep recoverable project state: record the shot name and prompt id at submission, and record retries, rejected takes, canonical references, and decisions that make earlier outputs stale. Append a new retry id rather than overwriting the failed one. The CLI journal records runs, but does not know why a visually completed result was rejected.

Choose graph fan-out versus independent shots using [workflows.md](workflows.md). Independent paid shots can be retried and reviewed separately; shared in-graph stages avoid repeated transfers. A decision to rerender still needs to fit the user's spending and retry scope.

At conform time, use measured clip durations, dimensions, frame rates, and audio windows. Trim/retime to the requested runtime, place voiceover within its beat, and duck music under speech. Loudness targets depend on the destination; a value such as -14 LUFS is a delivery choice, not a universal acceptance threshold.

## Present and verify the actual result

Show representative images or a video contact sheet, then the prompt/recipe and meaningful parameter changes. A path alone does not let the user judge the work. Keep the original media available as well as its preview.

`comfy preview` produces an image thumbnail, video contact sheet, or audio waveform. In the reviewed implementation, ffmpeg is bundled but ffprobe is not: without ffprobe, duration/fps/audio facts can be null and the contact sheet can cover only the first second. Check the metadata and timeline coverage before treating a preview as evidence about the whole clip. Use the software-installation skill if a missing media tool actually needs installation.

Inspect the affected frames, continuity transitions, duration, and final mixed sections. A waveform or volume measurement can reveal silence or buried speech; it does not establish pronunciation, accent, performance, or musical quality. Claim audio listening only when a supported tool actually provided it; otherwise ask the user to judge the sound.
