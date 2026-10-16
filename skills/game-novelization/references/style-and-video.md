# Original style and video details

## Build a style profile from the original

Summarize the experience the original seeks to give players from its actual presentation. Creator interviews and official statements may support this, but do not present personal guesses as production intent. Do not stop at genre labels such as fantasy, horror, or science fiction, or infer the game's literary style from a walkthrough writer's or streamer's tone.

Record a few actionable conclusions in the style profile in `project.md`, linking the scenes that support them:

| Observation dimension | What it determines in the novel |
|---|---|
| Narration and emotion | The actual blend of austerity/warmth, irony/sincerity, despair/hope; allow changes present in the original |
| Narrative voice | Current viewpoint and narrative distance, diction formality, sentence rhythm, rhetoric, and pauses; calibrate using the same game and approved passages in this book |
| Character dialogue | Formality, brevity/complexity, humor, subtext, forms of address, and differences between characters |
| Pacing and ambiguity | Where the original is urgent, slow, or silent; when to explain and when to let readers understand on their own |
| Visuals and space | Recurring light, materials, scale, and compositional relationships; choose features useful to experience or action |
| Sound and music | Environmental sound, silence, sound distance, and emotions created by the original score; distinguish sounds characters can hear |
| Themes and value conflicts | Choices, costs, and contrasts through which the original expresses themes; avoid concluding for it through new narration |

For the current plot segment, 3–6 concrete style rules suffice, for example: retain the character's restraint in speech, carry grief through pauses and consequences that have already occurred, and do not make impassioned declarations on the character's behalf. Tag conclusions with original evidence and mark them provisional when material is insufficient; do not expand the setting to fill a quota.

Different chapters may carry different emotions. Light everyday scenes need not be ominous merely because the book is classified as horror, and sudden original humor should not disappear for stylistic uniformity. Continuation checks should respect both whole-book traits and variations native to the current scene.

Record the current scene's voice and functional choices in the same profile, such as solemn forms of address, hesitant ellipses, ritual repetition, or supported narrator commentary; do not create a separate whitelist of banned words. Writing, polishing, and review reuse the same agreements, resolving conflicts dimension by dimension through the natural-narration reference. Style consistency does not mean identical chapters, and reducing AI-like prose must not override deliberate original expression.

## Use user-downloaded walkthroughs

First inventory the provided filenames, formats, and coverage, identifying original/remake editions, DLC, routes, and update dates. Read the actual contents and prioritize reusing them for event order, triggers, locations, key items, and ending prerequisites. Search online to fill gaps rather than ignoring existing materials and searching the entire web again.

Use available tools suited to the format: read plain text/Markdown/HTML directly; use the corresponding file skills for PDF, Word, and similar formats. List archive contents before processing only needed files; do not execute bundled programs of unknown origin. Record source paths and pages/paragraphs, retaining authors and original links when provided.

A guide's recommended order, optimal tactics, skipped route, or author interpretation may not be the only story. Distinguish achievement recommendations from main-story requirements. A guide omitting dialogue does not prove the original lacks dialogue or cutscenes.

## Use walkthrough videos or game recording files

When videos are provided, prioritize obtaining audiovisual details as completely and accurately as possible. The user has explicitly allowed token and time expenditure for this. Do not reduce viewing coverage, density, or verification depth to save resources, accelerate delivery, or reduce tool calls, and do not repeatedly ask whether further detailed viewing is worthwhile. Unless the user explicitly limits the time range or spoiler scope, review every provided video in full by default.

Gather sufficient material before deciding narrative emphasis. Walkthroughs, automatic subtitles, sparse thumbnails, and key-cutscene compilations help navigation but cannot replace full detailed viewing. Do not skip environment, character responses, or dialogue during review because a segment may later be summarized in the novel.

1. **Inventory**: inspect duration, tracks, resolution, and segmentation. Verify edition, route, editing, MOD use, commentary, speed changes, and skipped cutscenes. Number multiple files separately and always pair timestamps with file IDs to avoid confusing each episode's `00:10:00`.
2. **Build a timeline and coverage table**: use chapter markers, guides, subtitles, and navigation previews to divide every video into continuous segments. Record pending viewing, viewed in detail, or requiring another look, plus audio/visual/subtitle access for each. Leave suitable overlap at boundaries to avoid missing dialogue, actions, or shot changes spanning segments. Navigation previews do not count as detailed viewing.
3. **Review completely and in detail**: inspect each segment's visuals, available sound, and subtitles in order, capturing character actions, orientation, gaze, expressions, pauses, spatial relationships, furnishings, text, objects, sounds, and environmental changes. Check travel, waiting, minor NPC dialogue, and failed attempts for unique content before deciding whether they belong to the main story or deserve inclusion.
4. **Recheck details repeatedly**: revisit context around quest turns, key dialogue, subtle expressions, brief text, fast actions, environmental clues, and ambiguities. Where needed, slow playback, increase frame-extraction density, examine frame by frame at the original frame rate, enlarge regions, separate available audio tracks, and listen again. Do not infer continuous action from one image or replace listening to key dialogue with automatic subtitles.
5. **Create scene evidence cards**: record identifiable start/end times, characters, space, action sequence, expressions/pauses, objects, light/environmental changes, in-game sounds, dialogue, outcomes, and original atmosphere as fully as possible. Details not yet selected for the novel may remain in this task's temporary cards for later choice. Keep observation, inference, and external commentary separate.
6. **Update main-story and chapter cards**: link events, scene evidence, and chapters. After sufficient observation, decide which details to use, scenes to expand, and repetitive processes to compress. Thorough detail collection does not mean every observation belongs in the prose.
7. **Recheck coverage and blind spots**: inspect each segment for missed viewing, jumps, obstructions, brief content, and absent audio tracks. Continue filling accessible blind spots until the full scope has undergone the corresponding review and resolvable doubts have been checked. Preserve genuine limitations where tools or source material prevent access; do not mark those portions fully watched or invent content to complete records.

Prefer video-understanding, image-viewing, audio-transcription, and media tools available in the current environment. Before local frame extraction, check for `ffprobe`/`ffmpeg`. Follow `software-installation` for installation and `python-environment` for dependency setup. Do not install packages globally without authorization or upload original videos to external transcription services on your own.

These basic commands are examples for use as needed. Quote actual paths safely, place outputs in this task's temporary directory, and avoid overwrites. Replace `HH:MM:SS` with an identified timestamp:

```bash
ffprobe -v error -show_format -show_streams -of json 'input.mp4'
ffmpeg -n -ss HH:MM:SS -i 'input.mp4' -frames:v 1 'scene-frame.png'
```

Choose frame extraction, segmentation, transcoding, and audio processing according to detail needs. Do not cap total review volume, duration, or revisit count to save tokens or time; each request and current context must still follow the budgets in [Media capacity and checkpoint recovery](media-context.md). If continuous viewing is unavailable, reconstruct the sequence using dense frame extraction by segment and aligned audio/subtitles. Increase density further for brief expressions, text, and rapid action, retaining and viewing every source frame in relevant segments when needed. Sparse sampling from start to finish is not continuous full viewing.

Batch processing and temporary media management support execution, not reductions in necessary review. Retain enough resolution to identify text, expressions, and objects. Contact sheets serve navigation; open relevant original frames or crops when thumbnails are unclear, and do not default every contact sheet to `detail: original`. Save coverage and detail indexes batch by batch in a separate temporary workspace, and hand off context while payloads are still small. Separate calls, saved notes, or deletion of local images do not automatically remove images already in the conversation. Continue in batches to completion without downgrading the task to a summary because of length. If safe continuation is genuinely unavailable, follow recovery procedures to save the exact stopping point and report the specific limitation.

Judge research completion by actual coverage, discernible detail, and resolved doubts. Clear material without unresolved issues does not need mechanical endless repetition. If video access is unavailable, say so and proceed with readable material without claiming detailed video review.

## Distinguish four layers in videos

- **In-game events and sounds**: evidence for character actions, environment, dialogue, and space.
- **Score and camera presentation characters cannot perceive**: inform novel rhythm, narrative emphasis, and atmosphere; do not write characters hearing background music or seeing camera cuts.
- **Player operations, UI, pauses, reloads, and failed attempts**: identify the process; whether they become story events depends on the original mechanisms.
- **Commentary, scrolling viewer comments, editor-added subtitles, and streamer reactions**: external commentary or navigation clues only. Without verification, do not turn them into original dialogue, character motives, facts, or this book's narrative voice.

Automatic subtitles and OCR may misspell names, omit negation, or mix speakers. Rehear/review key commands, promises, identities, and truths, or check reliable text. If audio is unclear, retain the gap rather than inventing a continuation from automatic transcription.

## Allocate detail by narrative role

| Scene role | Recommended treatment |
|---|---|
| Key decisions changing the main story, relationships, or understanding; central dramatic sequences and finale | Fully develop action, dialogue, pauses, space, and consequences, incorporating useful video evidence |
| Quiet passages, exploration, and environmental storytelling important to the original style | Keep enough space to establish atmosphere, clues, or emotional transitions; do not omit everything without combat |
| First presentation of important rules, abilities, places, and enemies | Show perceptible features and their effect on action; do not reintroduce them in later repetition |
| Repeated travel, grinding, similar collecting, and operations without new information | Briefly summarize or omit while retaining necessary time, resource use, arrival, and outcomes |
| Pauses, menus, commentary chatter, real-world interruptions, and non-story reloads | Exclude from the novel except for mechanisms with explicit narrative significance in the original |

Allocate length by **causal importance, character change, emotional function, original dramatic emphasis, and the amount of first-time information**. A ten-second key choice may need more prose than ten minutes of travel. A long silence may carry a theme and must not be compressed solely because there is no gameplay operation.

Detailed writing is not a pile of adjectives, camera directions, or body parts. Select details that explain space, change action, convey emotion, reveal relationships, or preserve the original's identity, and remove repeated annotations of the same information. Video detail deepens established scenes rather than authorizing new causality.
