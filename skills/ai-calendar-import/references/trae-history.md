# Local TraeX History

The current extractor targets the TraeX / traecli `~/.trae/cli/` layout verified in this environment; it does not promise compatibility with all Trae IDEs. Honor TRAECLI_HOME, or cli under TRAE_HOME.

## Verified sources

- `state_5.sqlite`: thread IDs, sources, names/titles, and rollout paths.
- `thread_history_1.sqlite`: the `thread_items.userMessage` projection, including message creation times in milliseconds and structured content.
- `sessions/**/rollout-*.jsonl`: older `event_msg.user_message` and newer `history_mutation` entries, which can supplement materials lacking projections.

Open databases with mode=ro / query_only; do not modify source files or journal mode. When a consistent copy is needed, use the SQLite backup API instead of copying only the main file of a WAL database.

## Counting rules and limitations

1. Process only the user's own interactive threads with source=cli. Skip exec and subagent threads by default; define a separate counting policy if automated tasks need to be included.
2. Prefer structured user message projections when present, without also adding raw log counts. Raw user-role entries may be AGENTS instructions, environment information, skills, compaction summaries, or replays.
3. Without a projection, accept only explicit `event_msg.user_message` entries or messages containing `user.text` and an original `create_time`. Use original timestamps and local content fingerprints to remove obvious replays; mark fallback counts estimated.
4. Compaction regenerates item IDs, so IDs alone cannot deduplicate messages. In an observed long task, 81 user snippets and 27 distinct user.text item IDs corresponded to only 1 original creation time and 1 projected input.
5. Mark projections containing rollback/revision controls estimated. A projection may retain only the currently visible path and cannot guarantee all inputs ever sent and later rolled back are included; keep import coverage partial.
6. Format migrations, inherited branches, and older timestamp precision may create duplicates that cannot be judged automatically. Review specific conversations when clear anomalies appear; do not broaden fuzzy deduplication to hide differences.
7. Group by user message time; do not filter out later-resumed old conversations by the rollout file's creation date. The script checks all available interactive threads before filtering by the requested dates.
8. Do not estimate time spent. First/last fields store only recoverable message timestamps, with time=observed_timestamps and spans=[].
9. Older projections with created_at_ms=0 have unknown timestamps; do not interpret them as 1970 and silently discard them through date filtering. If all timestamps in a user projection are zero and the raw log still exists, replace the entire projection with explicit user events from the log, keep estimated, and do not add the two together; old projections may contain only the latter part of a conversation. For other projected messages lacking send times, use thread_turns.started_at to establish the turn's date when possible, set time=date_only and first/last times to null, and do not treat turn start as the send timestamp. If even the date cannot be established, fail explicitly instead of guessing.
10. When a rollout is missing, still inspect the message projection; preserve the projection and turn metadata in the archive and note that the original log is missing. Do not skip messages that remain recoverable. Do not infer send counts from titles or empty conversation metadata alone.
11. Very old history_mutation.append entries may contain only turn_id, without content_item_kinds / create_time or a projection. The script places these candidates in unresolved_legacy_threads in the context and returns requires_manual_review; do not automatically count raw user roles or report completion as empty history. Review raw lines individually, distinguish real input from AGENTS instructions, skill reminders, and compaction summaries, recover only confirmed initial append entries, and record line numbers and item_id as private evidence. Do not count replace replays again; keep supplemental records estimated and also supplement the full archives.

Output includes candidate calendar JSON, review context with a few user snippets and legacy-format candidates requiring verification, and full per-conversation `.jsonl.gz` archives referenced by `archives/index.json`. Archives save normalized messages for all available user, AI, tool, and system events, and preserve available rollout snapshots, projections, and raw turn rows byte for byte; they do not save only user sends. Zero message timestamps become null in the normalized archive, while raw rows retain their zero values. Archive sampling is not limited by `max-snippets`; counting still follows the rules above.

Archive each selected conversation together with its context outside the date range. The default archive directory is archives beside the candidate file; override it with `--archive-out-dir`. Use `--summary-only` only when the user explicitly requests summaries alone. Prefer projections for reading; preserve revisions, replays, and unfinished final lines in raw rollouts for future parsing.

Context is for summarization and must not be uploaded to the calendar API. Defaults are at most 8 snippets per record and 800 characters per snippet; when necessary, use `--max-snippets` and `--snippet-chars` to expand the specified scope, or conduct additional read-only investigation of one conversation.

Locally active threads continue to change, so the extractor marks candidates for the current calendar day partial. After reviewing the snapshot available at extraction time, still judge organization progress according to SKILL.md and set final when appropriate. Add later content using stable IDs; do not leave a record perpetually pending merely because its conversation remains active. A successful script run does not justify changing completeness declarations to complete. Obtaining truly complete history first requires complete source retention and export coverage.
