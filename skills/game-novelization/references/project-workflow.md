# Projects and continuation

## Work directory and temporary workspace

Prioritize the user's designated work directory. If none is specified, use `game-novels/` under the current writing workspace. If the current directory is a skill repository, software source repository, or system directory, use `~/Documents/game-novels/` instead and state the location when saving begins. Do not commit novels, full source texts, or runtime state to the skill repository.

Distinguish each work by game title, edition, and route, for example `game-novels/game-title/original-routeA/`. Check existing works first and reuse them when continuing, rather than making a new copy for each session. Keep different editions or mutually exclusive routes independent; they must not share chapter progress.

The final work directory contains only the novel text and normal chapter files, not research, outlines, state tables, or review attachments. Do not evade the novel-only delivery rule through hidden directories, appendices, or sidecar files. If the user explicitly requests an outline, review, or research, deliver according to that request.

When internal material must be saved, create a separate temporary workspace for this task, record its actual path, and keep it outside the work directory. Copy templates from `assets/project-template/` as needed, without overwriting existing files or prebuilding empty character and faction encyclopedias:

```text
task-temporary-workspace/
├── project.md              # Work, edition, route, style, and user agreements
├── source-notes.md         # Read sources, key facts, video evidence, and gaps
├── plot-and-chapters.md    # Main-story events, dependencies, conditions, detail levels, and chapter mapping
├── continuation-state.md   # Valid state and next steps for the current task
└── chapter-log/
    └── chapter-001.md       # Source mapping, review scope, and state changes
```

Save the prose separately in the work directory; internal files only reference its actual location. Copy the `chapter-log.md` template per chapter into the temporary log directory, not into the prose. For a short trial passage in chat, provide the prose directly without supporting records or a mandatory project setup. Respect any user prohibition on file creation.

Compatibility with existing workspaces: `项目.md` → `project.md`, `原作资料.md` → `source-notes.md`, `主线与章节.md` → `plot-and-chapters.md`, `章节记录.md` → `chapter-log.md`, and `续写状态.md` → `continuation-state.md`. These are equivalent old and new template/workspace filenames; read and reuse existing files under their old names without requiring renaming. The new per-chapter log directory is `chapter-log/`; existing `章节记录/` directories and Chinese chapter filenames remain valid and must not be renamed merely for migration.

## Locating works in Yuyan

Use this only when the user requests saving to Yuyan or continuing a work there; local delivery conventions remain in effect. First read [yuyan-doc](../../yuyan-doc/SKILL.md) and its designated read/write references. Reuse that skill for connectivity, APIs, body format, revisions, and save verification.

The current archive hierarchy is the home-page group “游戏小说” → a separate novel knowledge base for each game → chapter documents. Existing novel knowledge bases use the naming form `《游戏名》`, with chapters directly at the root. Home-page groups and document directories within a knowledge base are different levels.

1. **Locate afresh every time.** Prioritize the document or location explicitly specified by the user. By default, read `book-groups` and `books`, find the home-page group “游戏小说” by name, and associate live knowledge bases through `bookIds`. Confirm the work using its game title, aliases, edition, and actual chapter content. Book-title brackets are only a name-matching clue, not proof of group membership; the same game's walkthrough knowledge base may be in “游戏攻略”.
2. **Connect to the actual chapters.** Read the target `books/ID/tree`, verify chapter order, document IDs, and current parent directories, then read the current drafts to be handled. After knowledge-base or directory changes, old document IDs may still work while old knowledge-base IDs and parent mappings are stale. Use old handoffs only as lookup clues, update this task's temporary state from current responses, and do not restore an old combined “游戏小说” knowledge base or old game directories.
3. **Create a separate knowledge base for a new work.** For existing works, reuse the knowledge base, name, and chapters. Once the absence of a corresponding work is confirmed and the user has requested saving, follow yuyan-doc's [knowledge-base operations](../../yuyan-doc/references/api.md#document-tree-and-knowledge-bases) to create a knowledge base within the home-page group “游戏小说”, including the current `groupId` in the request. If no name is specified, use `《游戏名》`. Distinguish coexisting editions or mutually exclusive routes in the name or directories without mixing progress.
4. **Place chapters at the root by default.** Omit `--parent` for new root-level chapters; do not add a game-title wrapper directory. Follow existing volumes, route directories, other subdirectories, and user requirements without automatically dissolving or rearranging them. Write only novel prose and normal chapter titles in the knowledge base, not sources, outlines, review tables, or continuation state.
5. **Verify unclear destinations first.** If the expected group is missing, multiple works cannot be distinguished, or creation fails, query again and use the user's specified location to resolve it. If still uncertain, ask about that item while retaining independently completable drafts. Do not fall back to a walkthrough library, an ungrouped destination, or a new old-style combined library. If a write result is unclear, inspect the actual result before acting.
6. **Record and verify.** Temporary state may record verification time and mappings between the home-page group, knowledge base, parent directory, and chapter documents. Do not put real IDs, prose, or directory snapshots in the skill repository. Verify group membership after creating a knowledge base using yuyan-doc. After chapter structure changes, check the tree once for the combined changes. For ordinary prose updates, rely on its built-in read-back verification; on conflicts, reread the current draft without overwriting user edits.

## Connect and start a new round

Read this book's agreements, currently available state, the planned chapter, the previous chapter's actual ending, and relevant evidence. Do not reread the entire book every round or continue solely from a chat summary.

If the previous task finished and internal material was cleaned up, rebuild the current state from the actual prose, existing conversation, and original sources the user still provides. Do not retain a reference library without authorization merely to simplify continuation. Preserve the user's names and file layout. Ask only about an edition, route, or deliberate authorial deviation that truly cannot be determined.

Focus on character location, party, life/death and injuries, item ownership, abilities, relationships/commitments, and known/misbelieved/unknown information. Record knowledge in the research separately from what a character knows, preserving the original revelation timing.

When an internal summary contradicts the prose, trace the actual text. If the prose contradicts the original, distinguish an old-draft error, unverified research, and an explicit user deviation; do not automatically turn an old-draft error into canon. Do not alter the user's manuscript to accommodate a summary.

## Internal file responsibilities

- `project.md` stores this book's settled agreements and style; a recommendation is not a user choice.
- `source-notes.md` stores evidence and its categories; prose, summaries, and novelization additions are not external evidence.
- `plot-and-chapters.md` stores stable event IDs and chapter mappings; renaming a chapter does not change an event's identity.
- `continuation-state.md` stores valid progress for the current task, distinguishing original constraints from this book's additions.
- `chapter-log/` stores per-chapter evidence, verification scope, and state deltas for current writing or revision. Reuse `章节记录/` in an existing workspace.

Split character, location, and faction entries only when material grows too large; their index also stays in the temporary workspace. Keep each game independent, without generalizing one book's setting or style to other works.

## Save order during writing

Track internal progress as planned / draft / awaiting verification / reviewed. User-confirmed is an additional status; no reply is not confirmation, and waiting for chapter-by-chapter approval is not the default.

1. Save the prose. If a critical factual gap exists, keep a temporary draft awaiting verification rather than placing it in the delivery directory as a final draft.
2. Check fidelity, continuity, and expression, recording the events and evidence actually checked internally.
3. Record this chapter's coverage, state changes, novelization additions, unresolved items, and ending position.
4. Update events as unwritten / partially covered / covered / route not applicable, with locations and reasons.
5. Update the valid state from actual prose and check results; unverified critical facts must not advance official continuation.

After an interruption, verify the files saved to disk before resuming. Do not skip missing prose merely because a record says complete. If the original has not been checked, retain the verification gap internally and disclose it during the work if needed; do not conceal it through a note appended to the final novel.

Save video research batch by batch as well: first persist observations and blind spots, then update actual coverage, returned images not yet organized, and the next frame/timestamp. Use the media-continuation fields in `continuation-state.md`. Handle context handoffs and oversized-content errors according to [Media capacity and checkpoint recovery](media-context.md). A new session reads state and evidence for the current segment first, rather than reloading all images, OCR, or whole-book research.

## Revisions and propagation of changes

Distinguish expression changes from factual/route changes. Language adjustments may leave state intact; changes to events, character knowledge, injuries, items, promises, foreshadowing, or time require checking directly dependent later chapters.

Repair within the authorized scope. Raise related out-of-scope issues during the work rather than quietly rewriting the whole book. After changing edition or route, recheck divergence points and coverage without reusing completion markers from the old route.

Preserve the user's manual edits and do not delete old drafts to rebuild state. Save a separate revised draft when necessary, identify the final adopted version during the work, and point final delivery links only to the novel completed in this task. Keep work content and raw game sources out of the skill repository.

## Further revision of existing works

When the user requests another polishing round on an existing novel:

1. **Set the baseline.** Locate the latest draft specified in the handoff or context. If delivery is to external documents, read all current drafts first and compare them chapter by chapter with local drafts. If the online draft has user edits, merge starting from it. Older drafts and historical exports are for comparison only and must not overwrite the current draft. Save pre-revision snapshots separately in this task's temporary workspace, and revise independent copies.
2. **Read through before editing.** Read the authorized scope continuously as someone who has never played the game. Note comprehension gaps, motivation gaps, walkthrough-like narration, dragging or overexplained passages, and writing worth preserving. Handoff problem lists and experience are only leads; do not assume this round must lengthen or shorten the work, or defend the previous round's changes.
3. **Choose the level from actual problems.** After multiple polishing rounds, a manuscript often has only targeted issues left; volume of changes is not a quality measure. Fix structure, information order, or character-knowledge errors before expression.
4. **Handle cross-chapter effects.** After adding setup, removing premature knowledge, or standardizing names, search related terms and recollections across the book to confirm consistency. Verify additions involving original facts according to the research reference.
5. **Write back and verify.** Generate the smallest diff against the pre-revision snapshots and do not write unchanged chapters. Where previews are available, first confirm that the preview exactly matches the final draft. Write in chapter order and inspect the destination tool's actual success receipts. On conflict, reread the current draft before preparing a patch. If the result is unclear, check whether the write actually happened before retrying. Read back and verify after all writes finish.
6. **Clean up and deliver.** After confirming successful saving, clean up only this round's snapshots, patches, read-back files, and notes, retaining the latest final draft. The final response gives only actual links and necessary progress conclusions.

## Write handoff notes

When the user requests a handoff, or the task clearly needs another session and temporary state will be cleaned up, make the notes sufficient for a new session to start without reading the old conversation:

- Work scope, edition and route, viewpoint, and the user's explicit requirements and latest feedback;
- Latest-draft location and how to identify it, older-draft locations with a comparison-only note, and external document locations, IDs, and last successfully written versions;
- What the previous round actually did and cleaned up, which sources remain, and which no longer exist;
- Original boundaries and character-knowledge limits easily mishandled during expansion, noting that they require rechecking and do not represent the entire original;
- Safety constraints for writing back and the user's workflow preferences.

Handoff notes are working files for agents. Keep them outside the work directory and out of the novel.

## Completion and cleanup

If the entire main story or multiple chapters are authorized, complete the full request rather than stopping at the outline. If actual output or tool limits intervene, save completed portions and a temporary continuation point, explain what truly remains, and do not call a synopsis or partial draft a complete novel.

After completing this request, first confirm the prose is saved and readable, then clean up the reference copies, source tables, video frames, audio extracts, evidence cards, plans, and review files generated for this task. Clean only clearly recorded temporary paths created by this task and no longer serving unfinished work. Do not delete user inputs, original downloads, videos, manuscripts, or other tasks' files. If cleanup scope is uncertain, do not delete, and do not deliver temporary research as attachments.

An unfinished large task may continue using separate temporary state. When it ends, do not automatically establish a permanent research library or leave hidden attachments. Future continuation rechecks the novel and the user's original sources.

Local novel files are the default delivery. For Yuyan or another user-designated destination, use the appropriate skill and actual success receipts, writing only the novel text. Without an external-write request, do not create knowledge bases, publish, or push the novel. The final chat response contains only the novel text or actual delivery links, without completion explanations, sources, character-count reports, or review results.
