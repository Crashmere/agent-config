# Local Antigravity Desktop History

Use these rules when collecting conversations from the Antigravity desktop app. The layout below was verified on macOS; inspect the actual files and SQLite schemas before reusing an extractor from another task. Keep temporary drafts, snapshots, and credentials outside Git.

## Verified sources

Conversation data lives under `~/.gemini/antigravity/` (the Electron runtime directory `~/Library/Application Support/Antigravity/` stores browser/window state rather than chat history):

- `conversation_summaries.db`:
  - `conversation_summaries`: `conversation_id`, `title`, `step_count`, `last_modified_time`, `workspace_uris`, `status`, `source`, `agent_name`, `parent_conversation_id`, `nesting_depth`, `last_user_input_time`, `last_user_input_step_index`.
  - `conversation_parents`: maps child `conversation_id` to `parent_id`.
  - `conversations_fts`: full-text index (`user_body`, `agent_body`, `last_step_created_at`).
- `brain/<conversation_id>/.system_generated/logs/transcript_full.jsonl`: full, untruncated JSONL log of conversation steps (`step_index`, `source`, `type`, `status`, `created_at`, `content`, `model`, `input_tokens`, `output_tokens`, `thinking`, `tool_calls`). Prefer this file over `transcript.jsonl`, which truncates long fields (`truncated_fields`).
- `conversations/<conversation_id>.db`: per-conversation SQLite WAL database (`trajectory_meta`, `steps`, `gen_metadata`, `executor_metadata`, `parent_references`, `trajectory_metadata_blob`, `battle_mode_infos`), where `steps.metadata` and `steps.step_payload` are protobuf blobs (`step_type = 14` corresponds to user input).

Open SQLite databases read-only (`mode=ro` / `query_only`); when taking a consistent snapshot of a WAL database, use the SQLite backup API rather than copying only the main `.db` file.

## Counting and archive rules

1. Distinguish desktop conversations from CLI and subagent threads: in the verified layout, desktop conversations have `source = ""` (whereas CLI entries have `source = "CORTEX_TRAJECTORY_SOURCE_CLI"`). Exclude subagent/nested threads where `parent_conversation_id != ""` or `nesting_depth > 0` (or listed in `conversation_parents`) from independent user-send counts; they may be referenced only as context.
2. Count only entries with `source == "USER_EXPLICIT"` and `type == "USER_INPUT"` in `transcript_full.jsonl` as recoverable user sends (`user_message_count`). Do not count `SYSTEM` / `SYSTEM_MESSAGE` notifications, `MODEL` / `PLANNER_RESPONSE`, or `GENERIC` tool-output steps.
3. Each `USER_INPUT.content` wraps the user's text in `<USER_REQUEST>...</USER_REQUEST>` alongside injected system blocks such as `<ADDITIONAL_METADATA>` and `<USER_SETTINGS_CHANGE>`. Read `<USER_REQUEST>` when summarizing topics, while preserving the full raw `content` unchanged in archives.
4. `created_at` timestamps are UTC ISO-8601 (`...Z`). Convert to the record's target timezone (for example `Asia/Shanghai`) before grouping into daily snapshots (`<conversation_id>:YYYY-MM-DD`). Keep `first_activity_at` / `last_activity_at` as observed message timestamps (`quality.time = observed_timestamps`, `spans = []`).
5. Preserve full conversation context across days in the normalized archive (`archive_conversations.py pack`), attaching `transcript_full.jsonl` (and any scoped `.db` snapshot or user-supplied files) via `--source-file` without truncating multi-day threads.
6. When `transcript_full.jsonl` is absent for an entry in `conversation_summaries.db` (such as older CLI-only summaries without local brain/conversation files), do not silently report zero sends as complete history: inspect `conversations/<id>.db` if present, keep `coverage` as `partial` or `unknown`, and record the missing log explicitly.
7. Active desktop conversations continue to grow while open; mark the current day's draft `partial` if still in progress or `final` once available materials have been reviewed, and update later via `--upsert` using the same `source` and `external_id`.
