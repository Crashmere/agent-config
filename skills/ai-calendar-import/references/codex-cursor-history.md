# Local Codex and Cursor History

Use these source-specific rules when collecting local conversations. The layouts
were verified on macOS; inspect the actual schema before reusing a private
extractor from an earlier task. Keep conversion code and real materials outside
Git, and replace hard-coded task directories and dates before execution.

## Codex

Sources under `CODEX_HOME`, or `~/.codex` when unset:

- `state_5.sqlite`: thread identity, source, title, and rollout path.
- `thread_history_1.sqlite`: actual `thread_items.userMessage` projections and turn metadata.
- `sessions/**/rollout-*.jsonl`: full messages, multimodal content, tool events, system context, and compaction events.
- `history.jsonl`: supplemental user-input history, not an additional count when a projection already represents the send.

Open SQLite read-only with `query_only`; use a read transaction or SQLite backup
for a consistent snapshot. Snapshot the observed rollout bytes before conversion,
including an unfinished tail. Preserve the original path/name in source metadata,
not the new task-specific snapshot path: changing only a staging reference should
not create a different conversation snapshot on every import.

Count recoverable user-message projections from interactive threads. In the
verified layout their source is `cli`; subagent sources are structured JSON, not
another user account. Inspect other source values rather than assuming all are
interactive. AGENTS instructions, environment messages, skill contents, tool
output, and automatic continuations are not independent user sends.

Match an image-bearing rollout message to its projection using original turn
identity and unchanged user text when available. The projection timestamp and
rollout `create_time` can differ by slightly more than two milliseconds. A rigid
two-millisecond assertion is therefore insufficient; retain both originals and
verify identity instead of widening a fuzzy merge across nearby messages. Keep
embedded image data and structured content unchanged, without following external
image paths. Calendar counts come from the projection, not the number of matched
rollout representations.

Check every interactive thread with projected sends in the requested window
against the selected conversations. A sessions-directory scan alone can miss a
thread whose rollout is absent; preserve recoverable projections and explain the
missing log. Revision metadata differs between versions: the verified Codex
projection-state table has no `has_revision_controls` column. Inspect actual
rollback events when relevant instead of borrowing the Trae schema.

Retain the established daily ID format, such as `conversation_id:YYYY-MM-DD`,
and keep full conversation context outside the date window in its archive.

## Cursor

The verified sources are:

- `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`: `composerHeaders`, `composerData:*`, `bubbleId:*`, and referenced `agentKv:blob:*` data.
- `~/.cursor/projects/*/agent-transcripts/**/*.jsonl`: main and associated subagent transcripts.

Use a read-only SQLite transaction. Preserve the selected raw database values
byte for byte, along with full original transcripts and scoped referenced content.
Do not export unrelated application credentials or project files. Associated
subagents may supply archive context but do not add user sends.

Count actual user bubbles, excluding drafts and automatic simulated messages.
Interpret simulation flags against the current data; a flag alone does not prove
that a message was automated. Retain stable bubble/server identities to distinguish
real repeats from branch replays. Identical text with distinct original sends is
not a reason to merge them.

Always audit main transcripts for explicit `user_query` entries in the requested
window, including conversations with a non-draft header but no user bubbles or
an empty `fullConversationHeadersOnly`. A real send can survive only in a
transcript even when the SQLite body is absent. Supplement its daily record and
archive; do not interpret an empty message projection as empty history. Reuse
the established source and conversation ID rather than creating a new namespace.

Compare transcript sends with the SQLite representation before adding counts.
Repeated timestamp/text blocks can be replayed context, but minute-resolution
timestamps alone cannot distinguish all repeats: confirm duplicates using source
identity, the primary projection, or individual review. Exclude timestamp-only
messages, available-subagent descriptions, and automatic completion instructions.
Preserve all of them in originals. Parse the explicit UTC offset in transcript
timestamps before grouping by the calendar timezone; do not assume UTC+8 for
history recorded in another location. If only the day is defensible, use
`quality.time=date_only` and null first/last times rather than borrowing a composer
creation time as the exact send time.

Reconcile newly extracted counts with prior records, especially earlier
transcript supplements. Never reduce an already confirmed count merely because
the primary database still lacks those messages. Source coverage remains partial
when deleted or unsynchronized history cannot be established; available daily
materials can nevertheless be fully organized and marked final.
