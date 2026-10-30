# AICalendar API and Client

Authoritative service contracts: [API documentation](https://github.com/Crashmere/AICalendar/blob/main/docs/API.md), [JSON Schema](https://github.com/Crashmere/AICalendar/blob/main/api/import.schema.json), and [synthetic example](https://github.com/Crashmere/AICalendar/blob/main/api/import-example.json). Read the local checkout directly when available; after configuration, GET `/ingest/v1/schema` to inspect the running version.

## Private configuration

The default is `~/.config/aicalendar/client.json`, targeting direct `nas` LAN HTTPS on port 443. Both configuration and token files must have permissions 0600:

```json
{
  "base_url": "https://YOUR_NAS_LAN_IPV4/aicalendar",
  "token_file": "/private/path/import-token",
  "ca_file": "/private/path/nas-local-ca.crt"
}
```

Do not write addresses or secrets into the repository. Read the token from a file; do not put it on the command line, in URLs, conversations, or environment logs. Without `--via-vps`, the client accepts only HTTPS to literal RFC1918 IPv4 LAN addresses (except local loopback demonstrations). It disables environment proxies for LAN requests and prohibits redirects, so credentials and upload bodies cannot be forwarded to another entrance.

The maintained private configurations all reference the same existing `token_file`; changing an entrance does not require copying or rotating the import token.

| Configuration | Entrance | Use |
| --- | --- | --- |
| `client.json` | LAN `nas` HTTPS 443 | Default for all service requests and new plans |
| `client-nas.json` | LAN `nas` HTTPS 443 | Explicit LAN configuration for existing NAS-bound plans |
| `client-vps.json` | Primary `vps` HTTPS 8443 | Only after the user explicitly requests VPS uploading, with `--via-vps` |
| `client-ali.json` | Compatibility `ali` HTTPS 443 | Retained legacy configuration; not an authorized route in this LAN/VPS import workflow |

The optional `ca_file` loads the public NAS local CA into Python's verified TLS context. The public certificate is not a secret and does not require mode 0600; never use the CA private key. Configuring this file lets default commands use LAN HTTPS without relying on the browser's trust store. If `ca_file` is omitted, Python's default TLS trust, including command-scoped `SSL_CERT_FILE`, applies. For an older LAN configuration without `ca_file`, use:

```sh
SSL_CERT_FILE="$HOME/ali/nas-local-ca.crt" \
  python3 scripts/import_records.py --config "$HOME/.config/aicalendar/client-nas.json" status
```

For explicitly authorized VPS uploading, use a separate private configuration with the primary public IPv4 entrance on port 8443, the existing `token_file`, and no NAS `ca_file`. Both scripts select `~/.config/aicalendar/client-vps.json` when `--via-vps` is present and `--config` is omitted. A custom VPS configuration must have exactly the same `base_url` as this primary configuration; `--config` alone never authorizes a public request.

```sh
python3 scripts/import_records.py --via-vps status
python3 scripts/archive_conversations.py --via-vps submit --plan /private/task/vps-archive-plan.json
python3 scripts/import_records.py --via-vps submit --plan /private/task/vps-plan.json
```

Before starting an import, check `status` through the selected route. On a LAN connection failure, stop without automatically retrying or falling back to VPS, ALI, tunnels, or an environment proxy. Each client also performs an 8-second read-only check before its first upload body, without repeating the check for every archive chunk. A VPS request failure never changes the selected route; only bounded retries within that explicitly authorized route are available.

The public VPS and compatibility ALI entrances use normal public certificate trust. All three entrances reach the same live AICalendar state on NAS, but the existence of these routes does not authorize their use for imports. The frozen original ALI installation is a separate migration-point fallback, not the target of compatibility client requests. See [server operations](../../server-operations/references/nas-migration.md) for host roles and recovery limits.

Import credentials are limited to `/ingest/v1/`: Schema, batch preview/submission, batch lists/receipts, normalized record queries, and chunked imports, queries, and downloads of full conversation archives. They cannot edit website annotations, use calendar summary export, delete data, manage portal devices, or read other applications. Downloading a full archive is distinct from calendar summary export; see [archives.md](archives.md).

## Fixed plans

`prepare` generates fixed requests for this task, with at most 200 records per batch by default and room left below the payload size limit. `--upsert` first reads existing record versions. The plan includes the destination address, content digest, stable idempotency keys, and all batches; coverage declarations go last and are submitted only after preceding records succeed.

Both activity and archive plans record the exact `base_url`, including the port and application prefix; the client rejects a plan whose destination differs from its current configuration. Use the matching authorized route for every preview, submission, or retry. Existing VPS-bound plans require explicit VPS permission and `--via-vps`; existing ALI-bound plans are preserved but are not authorized by this LAN/VPS workflow. Preserve the original plan and its digest; changing the default entrance does not authorize rewriting the destination or selecting a public route. A genuinely new destination requires a new plan from the reviewed source materials, while retaining existing IDs and respecting already committed data on the same NAS service.

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
| Network failure | Stop on LAN failure without automatic retries or public fallback; once the authorized route is reachable again, resume the original plan and confirm receipts/read-back |
| Plan digest/destination mismatch | Do not modify the plan to bypass validation; generate a new plan from the reviewed input |

The service commits each batch transactionally; a conflict writes nothing from that batch, but earlier successful batches remain committed. Client read-back checks batches and also compares actual record dates, counts, topics, and tags.
