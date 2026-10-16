# ChatGPT Web Exports

Read this reference when the user specifies a ChatGPT export ZIP, JSON, or HTML file. Export formats change, so inspect the actual structure first; do not interpret the absence of an old filename as the absence of conversations. This document supplements source identification and conversion rules; follow the main skill and `archives.md` for packing, uploading, retrying, and reading back.

## Confirm export scope

1. Record the original ZIP's SHA-256, create a fixed private source copy, and check archive integrity and the file inventory. Prefer reading individual members instead of extracting untrusted paths without inspection.
2. Check for both a single `conversations.json` and sharded `conversations-*.json`. If an export manifest exists, use its file list to verify names, sizes, and shard coverage; do not read only the first shard. Without a manifest, record the files actually found and do not assume full coverage.
3. Parse each relevant JSON file and check conversation IDs, message IDs, parent/child relationships, and empty conversations. If `chat.html` contains embedded conversation data, compare its parsed content as a cross-check; do not extract conversations solely from visible page text.
4. Conversation creation or update times do not represent every user's send date. Group each user message by its actual timestamp and the selected timezone, and report the message date range and export time separately. Keep missing timestamps unknown instead of turning zero values into dates in 1970.

## Message trees and send counts

- `mapping` is usually a message tree that may contain branches created by edits, retries, and regenerations. Traverse all nodes instead of following only the parent chain from `current_node` for the current branch; preserve parent/child relationships, original positions, and stable IDs.
- Generate the full archive in a stable order that respects parent/child relationships; sorting only by time must not put replies before parent messages. Empty root nodes and `message=null` do not count as sends, while real empty messages remain in the original archive.
- Identify recoverable sends by distinct user message IDs, distinguishing user, model, tool, and system nodes. Do not deduplicate by text: two sends with identical text, or sends with different IDs on edited branches, may both be real records. Investigate duplicate IDs or anomalous roles before counting them.
- An empty body does not necessarily mean no send: attachment uploads, audio content, or quoted follow-up information such as `targeted_reply_label` may carry user input. Verify against node structure and preserve the specific counting basis; do not apply a blanket `if text.strip()` filter.
- Each calendar record is a daily snapshot of one conversation. Construct a stable `external_id` from the conversation ID and date, split statistics across days, and preserve the full conversation without truncation. Archive empty conversations with zero user sends without inventing calendar activity.

## Audio, images, and attachments

- Inspect structured `content` recursively instead of collecting only strings in `parts`. Structures such as `audio_transcription` may contain text transcriptions; extract that text when reviewing topics, while preserving original structures and unknown fields in the archive.
- `asset_pointer` is a generic resource reference and does not by itself identify an image. Determine the type using its containing content type, resource path or extension, file metadata, and actual bytes; for example, a WAV reference is an audio resource. When the type cannot be determined, call it a “multimodal resource” and explicitly retain uncertainty.
- Exported attachments may use generic suffixes such as `.dat`. Identify images, PDFs, or other formats from export metadata and file signatures instead of extensions alone; preserve original filenames and bytes.
- Count resources referenced by conversations but missing their files separately from entries with file-library metadata but no files. Deduplicate by resource ID and list affected conversations; do not treat the number of metadata entries as the number of files obtained.
- When an audio file is missing but a transcription exists, state “语音实体缺失，转写保留” (audio file missing; transcription retained). Do not claim the audio itself has been archived or misreport missing audio as missing images. Save only attachments supplied by the export; do not automatically follow resource links to fill gaps.

## Original preservation and verification

1. Preserve normalized messages, all branches, and complete raw data. When per-conversation source files are needed, extract the exact raw objects from the original JSON shards; JSON parsed and then serialized again is a derived file and must not be described as a byte-for-byte original.
2. For large bundles, create a separate source archive using the export hash as a stable identifier, preserving the original ZIP and notes. Each conversation archive retains its own raw object and available attachments and records its association with the full bundle. This preserves the entire bundle without packing the same ZIP into every conversation.
3. Locally compare hashes of compressed files and expanded content, the results of reassembling segmented messages, and byte hashes of every embedded source. Check all user-node counts against total daily records instead of checking only whether uploads succeeded.
4. After uploading the fixed plan, verify receipts and hashes of the actual downloaded bytes. Report the original export as fully preserved only when the ZIP hash in the source bundle matches the user's original file.
5. Committed archives are immutable. If descriptions such as resource types are incorrect, preserve old snapshots, create revised snapshots, and state the scope of revision. Distinguish conversation counts from physical snapshot counts in reports; do not count revisions as new conversations.
6. Set records whose available materials have all been reviewed to `record_state=final`. If attachments are missing or complete platform history cannot be confirmed, preserve those limitations in source `coverage` and archive notes. Finally, report record counts, user send counts, date ranges, empty conversations, original file hashes, missing attachments, and read-back results.
