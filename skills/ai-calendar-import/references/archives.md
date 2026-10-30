# Full Conversation Archives

## Data and scope

Save immutable snapshots of each conversation, linked to daily records through `source + conversation_id`; save a new snapshot when conversation content grows and retain old snapshots. Deduplicate repeated uploads of the same content; never overwrite a completed snapshot. Do not replace message bodies, code, or tool results with summaries. The normalized format is UTF-8 JSONL + gzip; split long messages into segments without truncating them. Preserve original source files byte for byte and verify SHA-256. The authoritative service Schema is AICalendar's `api/archive.schema.json`; do not copy it into the skill.

Calendar counts still include only actual user sends; total archive message counts include AI, tools, system content, and other events, so they mean something different from usage counts. Hiding a summary does not delete its full archive.

Preserve the exports specified by the user, including supplied images, audio, attachment files, and unknown fields. When only URLs, local paths, or temporary resource IDs are present, retain the references and report that originals were not supplied; do not independently read local files outside the conversation or fetch external links. The Trae extractor preserves full rollouts and history projections by default, without automatically reading attachment paths mentioned in logs, other project files, or separate subagent databases. Its coverage is partial, indicating a snapshot of locally available materials; it cannot prove that platform history was never lost.

## Trae imports

`extract_trae.py` produces archives/index.json by default. For each archive listed there, run:

```sh
python3 scripts/archive_conversations.py prepare --archive /private/task/archives/THREAD.jsonl.gz --out /private/task/archive-plan.json
python3 scripts/archive_conversations.py submit --plan /private/task/archive-plan.json
```

These commands default to direct `nas` LAN HTTPS. Check `import_records.py status` before starting and stop on connection failure. Only after the user explicitly requests `vps` uploading, add `--via-vps` before the subcommand for archive preparation, submission, and downloads as well as summary commands. Keep each fixed plan bound to its original authorized entrance; see [API and client](api.md).

Oversized Trae conversations are automatically split into ordered volumes, and
`archives/index.json` includes every volume. The first volume keeps the original
conversation ID; subsequent volumes use `-volume-NNN`. Each volume preserves a
`reassembly.json` source file containing the ordered message volumes, original
source filenames, byte lengths, SHA-256 values, and exact source-part order.
Read message volumes in order; concatenate each original file's source parts and
verify its original SHA-256. Upload and verify every indexed volume before the
calendar summaries. Do not rerun extraction to recover an interrupted upload;
reuse the existing archives and fixed upload plans.

Complete archives before importing calendar summaries; each step is independently resumable, so do not claim an atomic batch commit across the two APIs. Trae extraction accepts `--source-label "Trae · 工作电脑"`; generic pack accepts the same parameter to override the displayed source label. The stable source does not change when the label is renamed. If archiving succeeds but summary import fails, retain the archive and original summary plan; stop on a LAN connection failure and resume that plan once its authorized entrance is reachable again.

Labels are stored in the service manifest. With the same gzip content, changing only source_label in the manifest, generating a new plan, and running prepare/submit again updates the displayed label without creating another snapshot. Do not edit an existing fixed plan or rewrite an original export merely to change a label. An omitted or empty label preserves the service's existing value. Synchronize calendar record labels separately through summary upsert; the two APIs do not modify each other. The website archive list supports filtering by label keywords.

## Other platforms

An external agent converts the export into local normalized JSON: source, conversation_id, title, coverage, note, messages, and optional source_label (the source label supplied by the user). Each entry in messages includes a stable id, role, at (with timezone or null), content (unchanged text or structure), and attributes (optional small metadata such as the original model or tool name). Use user, assistant, tool, system, developer, or unknown for role. Preserve message order, empty messages, and original languages; do not collapse multiple turns into a summary. Fields the conversion cannot represent must remain in the original export.

Structured values in normalized content are converted to JSON text for display; exact original types and unknown platform fields remain in the source files preserved byte for byte. Preserve original filenames separately, regardless of internal temporary snapshot names.

```sh
python3 scripts/archive_conversations.py pack --file /private/task/conversation.json --source-file /private/export.json --source-file /private/attachment.png --out /private/task/conversation.jsonl.gz
```

The normalized input file is also saved as original material. Repeat --source-file for additional files; packing first copies fixed snapshots, and later uploads use those exact bytes. Each archive is limited to 128 MiB compressed / 512 MiB expanded; fail explicitly if a limit is exceeded, save consecutive volumes, and state their ranges in note. Do not discard excess content or claim completion.

## Reliable upload and retrieval

`prepare` fixes the destination address, file path, overall SHA-256, and chunk list; `submit` uploads missing 384 KiB chunks, then asks the service to verify gzip, normalized message order, original-material chunks, and each source's SHA-256. Browsing is available only after complete verification. Finally, download the actual stored bytes and compare the overall hash and length. Retrying the original plan for a completed archive returns replay without adding a copy.

Preserve files and plans on network failure and stop the import rather than selecting a public route. Once the same authorized entrance is reachable again, execute the same submit to resume. For 400/409 responses, inspect the specific error; do not alter hashes, drop chunks, or reduce counts to bypass validation. A 503 means the service has not enabled the archive extension; complete maintenance before retrying.

Read back manifests in batches with `GET /ingest/v1/archives?source=...&offset=0&limit=100`, with at most 100 entries per page. The current API always returns next_offset equal to offset plus the number of entries on the current page; it does not use null to mark the last page. Stop when the current page is empty or shorter than the requested limit; otherwise, use the returned next_offset. Check all snapshot IDs, committed states, manifest hashes, and conversation associations; do not count revised snapshots as new conversations.

The website's “聊天存档” view lets users browse messages by snapshot and download `.jsonl.gz`. To restore everything:

```sh
python3 scripts/archive_conversations.py unpack --archive /private/download.jsonl.gz --out /private/new-directory
```

Output includes messages.jsonl with long messages reassembled, individual original-NNN.bin source files, and sources.json mapping filenames/types/hashes; each original file is verified. The output directory must not already exist. Do not write arbitrary paths based on source filenames. The service has no interface for automatically cleaning up full archives or deleting original text.

Saving an upload creates live NAS state, not an independent backup. The current AICalendar native SQLite backup includes the complete database: activity records, annotations, import audit, full conversation manifests, original-material chunks, message indexes, and unfinished uploads. A database snapshot alone does not include application programs, private configuration, host identities, or maintenance-client credentials. Follow the service's [operations documentation](https://github.com/Crashmere/AICalendar/blob/main/docs/OPERATIONS.md) and [NAS backup contract](../../server-operations/references/nas-migration.md#manual-full-backups) for manual full compressed recovery sets on verified external storage; routine NAS backup has no internal fallback or schedule.

Maintenance-side original files, plaintext import tokens, and unfinished upload plans remain separate materials. Preserve them for continued access and resumption, or explicitly include them in an agent-operated external backup. Do not delete local originals merely because uploading succeeded.
