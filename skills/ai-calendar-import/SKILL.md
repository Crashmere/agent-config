---
name: ai-calendar-import
description: "Import or backfill AI usage history into the personal AICalendar service, including TraeX history, user exports, previews, and verification."
---

# AI Calendar Import

Treat the service as the storage and presentation layer for normalized records. Interpret and convert source materials locally; the service does not need to connect to any AI platform.

## Boundaries and sources of truth

- Service source code and API contract: `Crashmere/AICalendar`, usually at `~/ali/AICalendar`. First read [API and client](references/api.md) and [Full conversation archives](references/archives.md). The authoritative JSON Schemas are the service's `api/import.schema.json` and `api/archive.schema.json`; do not keep separate copies in the skill.
- When reading TraeX / traecli, also read [Trae history](references/trae-history.md); when reading ChatGPT web exports, also read [ChatGPT exports](references/chatgpt-export.md). For other platforms, interpret the fields in the files specified by the user, preserve original identifiers and uncertainty, and do not apply the Trae format.
- Run only when the user requests organization. Do not add reporting rules to the global AGENTS file, hooks, resident processes, or scheduled tasks.
- The current agent summarizes titles, summaries, and tags; deterministic scripts extract times, counts, and stable identifiers. Do not infer counts, time spent, or dates from topics.
- Keep original conversations, temporary JSON, import plans, and credentials in private directories outside Git. The user has requested full conversation preservation: by default, each import also saves normalized messages and original export materials to the authenticated service. Do not treat summaries or a few review snippets as complete archives. Reading local files may still bring selected snippets into the current model; do not describe this as local model inference.

## Complete workflow

1. Determine the source, the source label supplied by the user, and the dates. When the user says materials come from ChatGPT or a Trae work computer, preserve that meaning as source_label (up to 80 characters), which may contain Chinese characters and spaces; source remains a stable account/source namespace, and changing a display label must not recreate source or external_id. The label is displayed and used for filtering in the calendar and full archives; do not mix it into topic summaries. If the user supplies no label, use the known source name without inventing an account or device. The user's specified range takes precedence; for the first request for recent history, default to 7 days. Subsequently, use `status` to check successful coverage first, then overlap the preceding 7 days to include late records. Do not treat an unknown range as already fully covered.
2. Create a separate private directory for this task under `~/.local/state/aicalendar/`. Read the source materials; for Trae, use the extraction script to generate candidate records, separate review snippets, and full conversation archives (enabled by default). For affected conversations, save all currently available context; date filtering controls only calendar statistics. Do not truncate the original text of conversations spanning multiple days.
3. Review the snippets, add read-only queries for individual conversations when needed, and produce concise titles, summaries of 1–3 sentences, and a few tags. Preserve source_label, edit topic fields in the candidate `records`, and set `quality.topic` to `agent_summary`. For long conversations, do not infer the entire day's topic from only the first few snippets; expand the sample for that conversation or retain a broader title. Check organization progress for each record: set `record_state=final` when the selected materials have been extracted and reviewed with no organization work remaining; retain `partial` when backfilling or review is still pending. Do not simply inherit the candidate state or infer record state from source coverage.
4. Confirm that each record is a complete daily snapshot of one conversation from one source. `source` is the account namespace, and `external_id` is stable; do not generate random IDs on reimport or add message counts to old values. Use null/unknown when original information is insufficient. Use `--summary-only` to skip originals only when the user explicitly requests summaries alone.
5. Follow archives.md to generate a fixed upload plan for each complete archive in `archives/index.json`, submit chunks, verify the service receipt, and download to compare hashes. Reuse the original plan after an interruption; do not repack. Commit full archives before importing summaries. Preserve original text unchanged, including unknown fields, tool arguments/results, original multimodal structures, and attachment files supplied in the export; do not read unrelated local files or download external links to fill attachment gaps on your own.
6. Run local `validate`, then `prepare` to generate a fixed plan that cannot be overwritten. For existing records the user wants completed, use `--upsert` to read the current version; use insert_only for ordinary first imports.
7. Run `preview` and check the counts of `final` / `partial` records and the specific reasons for retaining pending organization states. Continue directly with already authorized new imports. If there are actual overwrite conflicts, reductions in confirmed counts, deletions, or rollbacks, show the specific differences and act within existing authorization; do not change IDs to bypass deduplication.
8. Run `submit`. It previews each batch again, submits idempotently, verifies receipts, and finally reads back records. Retry network failures with the **original plan**. Do not change idempotency keys or skip failed batches to submit a complete-coverage declaration first.
9. Report the number of full archives, hash verification of original materials, missing attachments/sources, actual sources/date ranges, insertions and updates, retries skipped, unresolved conflicts, and data limitations, and provide the calendar link. On replay, inserted in the receipt is the original batch result; do not describe it as new insertions in this attempt. `superseded_records` means newer versions exist after the original plan succeeded; explain that current data has been updated instead of repeatedly submitting the old plan as though it failed.

## Commands

Resolve the paths below against the actual skill root. The scripts depend only on the Python standard library.

```sh
python3 scripts/extract_trae.py --from 2026-10-01 --to 2026-10-07 \
  --source-label "Trae · 工作电脑" \
  --out /private/task/draft.json --context-out /private/task/context.json
python3 scripts/import_records.py validate --file /private/task/reviewed.json
python3 scripts/import_records.py prepare --file /private/task/reviewed.json --out /private/task/plan.json
python3 scripts/import_records.py preview --plan /private/task/plan.json
python3 scripts/import_records.py submit --plan /private/task/plan.json
```

Place `--config /private/client.json` before the subcommand; the default is `~/.config/aicalendar/client.json`. `status` queries import coverage, and `lookup --source trae-personal` queries existing records (including hidden entries and versions).

## Record semantics

- `user_message_count` counts only recoverable messages actually sent by the user, including messages added during execution; subagents, tool calls, automatic continuations, and compaction do not count as the user's sends.
- Once the date, source conversation, and timezone are established, do not change them through ordinary upsert. The first version automatically blocks reductions in confirmed counts or data quality; use a controlled maintenance workflow for actual corrections.
- `first_activity_at` / `last_activity_at` may represent only message timestamps; when only timestamps are available, use `quality.time=observed_timestamps` and `spans=[]`. Do not subtract the first from the last to estimate time invested.
- Multiple activity intervals in one day can go in spans; split intervals crossing days according to the timezone. Unknown times are null; unknown counts are null with quality.count=unknown.
- `record_state` represents organization progress for this calendar record. `final` means the daily snapshot of the selected materials has been fully organized, displayed on the website as “已整理”; `partial` means organization work remains in this task, displayed as “记录待补全”. `final` still allows new materials through upsert with version checks; it does not mean all platform history has been obtained.
- `quality.count=observed` means only that sends can be directly identified in the selected materials; it does not guarantee the platform retained all history. Declare source and date-range completeness separately through `coverage[].status`; retain `partial` or `unknown` when uncertain. The full conversation snapshot's `manifest.coverage` is also independent of calendar `record_state`. Keep specific explanations for missing source images, missing message bodies, and similar gaps; a record whose available materials have been fully organized can have both `record_state=final` and `partial` source coverage.
- Titles, summaries, tags, and visibility changes made by the user on the website are stored separately; reimports must not overwrite that layer.
- Export bundles contain `activities[].record` and `activities[].annotation`. Explicitly extract record before reimporting; restoring annotations is a separate operation, so do not treat the export bundle directly as an import request.

When the skill or scripts encounter an actual format change, resolve the current task first, then correct this skill through personal-skill-management; never interpret an old format as empty data and report success.
