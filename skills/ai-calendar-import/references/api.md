# AICalendar API and Client

Authoritative service contracts: [API documentation](https://github.com/Crashmere/AICalendar/blob/main/docs/API.md), [JSON Schema](https://github.com/Crashmere/AICalendar/blob/main/api/import.schema.json), and [synthetic example](https://github.com/Crashmere/AICalendar/blob/main/api/import-example.json). Read the local checkout directly when available; after configuration, GET `/ingest/v1/schema` to inspect the running version.

## Private configuration

The default is `~/.config/aicalendar/client.json`; both configuration and token files must have permissions 0600:

```json
{
  "base_url": "https://YOUR_SERVER/aicalendar",
  "token_file": "/private/path/import-token"
}
```

Do not write addresses or secrets into the repository. Read the token from a file; do not put it on the command line, in URLs, conversations, or environment logs. The client enforces HTTPS (except local loopback demonstrations) and prohibits redirects to prevent forwarding credentials to other addresses.

Import credentials are limited to `/ingest/v1/`: Schema, batch preview/submission, batch lists/receipts, normalized record queries, and chunked imports, queries, and downloads of full conversation archives. They cannot edit website annotations, use calendar summary export, delete data, manage portal devices, or read other applications. Downloading a full archive is distinct from calendar summary export; see [archives.md](archives.md).

## Fixed plans

`prepare` generates fixed requests for this task, with at most 200 records per batch by default and room left below the payload size limit. `--upsert` first reads existing record versions. The plan includes the destination address, content digest, stable idempotency keys, and all batches; coverage declarations go last and are submitted only after preceding records succeed.

`preview` does not write business data; conflicts produce full JSON output and exit code 2, while ordinary errors use 1. `submit` previews each batch again, submits it, and reads back the receipt; preserve the plan on failure and submit the same plan again to resume. The service deduplicates by `source + external_id` and uses idempotency keys to prevent duplicate submissions on network retries.

When replaying an old successful plan, current records may already have been updated by later batches. The client distinguishes versions using the receipt: records at the same version are checked individually and counted in `verified_records`; higher versions appear in `superseded_records`, returning `committed=true, exact_current=false`. This means the original commit succeeded and updates now exist, rather than a network failure. Do not repeatedly retry or overwrite newer versions because of this result. Missing records, regressed versions, or different content at the same version still cause an error exit.

Different requests must not share an idempotency key. Concurrent updates to existing records may cause an old plan to conflict; read back the new versions and differences, then prepare new input and a new plan according to the user's goal. Do not independently overwrite the user's presentation changes or reduce confirmed counts.

Numbers in the JSON file are values for the current complete snapshot. If a record previously had 6 sends and new materials confirm 8, submit 8; do not add them to make 14.

source_label is an optional source label supplied by the user, up to 80 characters, allowing Chinese characters and spaces; both the calendar and archives display it. Keep source and external_id stable; rename a label through upsert with a new plan, without changing the source or accumulating counts. prepare --upsert retains the existing label when the input omits source_label and uses the new label when a nonempty value is supplied. Calendar query q includes source labels, and tag can match a source label exactly.

## Common errors

| Error | Action |
| --- | --- |
| 401 | Check private configuration and the currently valid token; do not try portal Cookies or disable authentication |
| 400 | Correct fields, time ranges, or quality explanations according to the running service's Schema |
| 409 | Read each reason and distinguish version changes, old snapshots, count reductions, and idempotency key reuse |
| Network failure | Retry with the original plan and confirm receipts and read-back results |
| Plan digest/destination mismatch | Do not modify the plan to bypass validation; generate a new plan from the reviewed input |

The service commits each batch transactionally; a conflict writes nothing from that batch, but earlier successful batches remain committed. Client read-back checks batches and also compares actual record dates, counts, topics, and tags.
