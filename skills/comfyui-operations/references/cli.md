# Comfy CLI operations

These references consolidate the useful contracts from the official [comfy-cli skill family](https://github.com/Comfy-Org/comfy-cli/tree/main/comfy_cli/skills), reviewed from versions 1.18.0 and 1.21.0. Command examples follow the 1.21.0 material. Use the installed command's `--help`, `comfy --json discover`, and live schemas to resolve version differences; do not upgrade an installation just to match an example. In particular, the newer surface uses `model`, not the older `models`, and hides deprecated nodes by default.

## Choose the backend before execution

Routing precedence is `--where` > `COMFY_WHERE` > the governing `comfy.yaml` project's `defaults.where` > persisted `comfy set-default --where` > auto-detection. Auto-detection can choose cloud when credentials exist. Use an explicit `--where local` for a local-only task rather than assuming that a local CLI means local execution.

`COMFY_LOCAL_URL` selects the local server address, not the backend. Its precedence is per-command `--host`/`--port` > `COMFY_LOCAL_URL` > a CLI-managed background server > `127.0.0.1:8188`. Inspect the resolved workspace and credentials without extracting secrets:

```bash
comfy --json env
comfy --json which
comfy --json cloud whoami
comfy --json cloud status
```

Cloud authentication prefers a live OAuth session, then `COMFY_CLOUD_API_KEY`, then a stored key. Setting a key does not override the live session; `cloud whoami` identifies the active method and base URL. Use the CLI's login/logout flow for a credential change. Do not upload tokens to a third-party decoder.

When `cloud status` reports `balance_confirmed: false`, a null balance is unknown, not zero. Read its explanatory `message` before reporting funds or choosing paid work.

## Discover capabilities and parse results

Use `comfy --json discover` for the command tree, output schemas, and error codes. Ordinary commands return an envelope with `ok`, `command`, `version`, `where`, `data`, and `error`. Read `error.code`, `hint`, and `details`; a suggested command still needs to fit the user's authorization and the actual failure.

```bash
comfy --json nodes ls --produces IMAGE --limit 10
comfy --json nodes search 'checkpoint loader'
comfy --json nodes show KSampler
comfy --json model list-folders
comfy --json model list-folder checkpoints
comfy --json templates ls --type image --limit 10
```

- `nodes show` exposes the target server's exact class, input types, outputs, and enum choices. Local and cloud catalogs may differ. Without a server, supported discovery commands accept `--input object_info.json`.
- `data.close_match: true` means a search returned similar names after finding no actual match. Nonempty rows alone do not establish that a requested class exists.
- `data.total` can exceed the rows returned under `--limit`. A node row's `is_api_node` distinguishes a partner API node; open-weight nodes on cloud can still consume cloud compute.
- `data.stale: true` or an `object_info_stale` warning means the schema came from cache. `nodes refresh` refreshes annotations, not the live `object_info` schema.
- Optional `data.knowledge` or `knowledge pick` results are recommendations, not an executable catalog. A missing block or `zero_hit` is not evidence that a capability is unsupported. Live schemas override cached prose, and the user's explicit model choice is not replaced merely by a ranking.
- With `knowledge pick --check-local`, missing models and `available_locally: false` identify installation gaps. A missing or unsuccessful `local_check` does not establish that an alternative is runnable. `templates check` can identify required files before any download.

For provider calls, `generate list --json` and `generate schema <alias> --json` expose aliases and parameter schemas. Successful `generate <alias> --json` calls can return the raw provider response rather than the ordinary envelope; `generate upload --json` returns a signed URL structure. Do not parse a pretty table or assume every success has `data.prompt_id`.

## Submit, track, and collect

Validate the workflow as described in [workflows.md](workflows.md), then choose one waiting model:

```bash
comfy --json run --workflow workflow.json --where local
comfy --json jobs watch <prompt_id> --where local
comfy --json download <prompt_id> --where local
```

`run` is asynchronous by default and returns a prompt id and a state-file path. `jobs watch` attaches to that job; `run --wait` is the synchronous alternative. A lost watcher or interrupted wait does not cancel server-side work. Check `jobs status <prompt_id>` and reattach before considering another submission.

`jobs ls` is scoped to the resolved backend; `jobs ls --all` includes tracked jobs across targets. For a deliberate batch of independent jobs, use `jobs wait <id>...` rather than a sleep-poll loop. `jobs watch` succeeds only on completion; inspect failed/canceled terminal results before downloading or starting a dependent stage. Prefer `outputs_by_node` and `outputs_by_item` over output-array order.

In the reviewed CLI, `run --timeout` bounds silence between progress events, not total runtime. Use a supported wall-clock bound such as `jobs watch --max-wait`, or a bounded batch wait, when the user needs a time limit.

`generate` is a separate provider-call surface, not a workflow job. It normally waits internally; deliberate async calls use that surface's `resume` command. `generate --emit-workflow` can produce a partner-node workflow without running a generation, making a one-shot prototype reusable.

Partner-node workflow runs use `--allow-spend`; provider `generate` calls use `--yes`. Noninteractive calls can fail with `spend_consent_required`. Pass the flag only for spending the user actually approved, and never change persistent consent merely to clear an error. CLI acceptance does not itself prove that cloud compute is free.

## Recover by failure class

| Evidence | Appropriate next step |
| --- | --- |
| `server_not_running` | Inspect `env` and `which`; start the intended local installation if startup is within scope. |
| `cloud_not_configured` / pre-submit `cloud_unauthorized` | Check the active session and base URL, then use the authorized login flow. |
| A terminal cloud job reports `transient_auth` mid-execution | This is a server-side partner token failure, not necessarily a CLI login problem. After confirming the job failed, consider one resubmit within the approved spending/retry scope. |
| `prompt_rejected` | Read `details.node_errors`; verify exact node classes, loader choices, required inputs, and graph links. |
| `workflow_invalid_json` | Check whether the saved file is actually JSON rather than an HTML download error. |
| `workflow_not_api_format` / `conversion_error` | Use the target schema for UI-to-API conversion, or export API format from ComfyUI. |
| `cql_no_graph` | Restore target reachability or use a valid offline `object_info.json`. |
| `ws_timeout` / `ws_disconnected` | Check the existing job and reattach; the server may still be executing it. |
| `cloud_timeout` | Check the existing job before resubmitting; a silence timeout need not mean execution ended. |
| HTTP error with XML authentication text | Verify the base URL and route; cloud ComfyUI endpoints are under `/api/`, while other paths can hit a CDN catch-all. |

For pending jobs, inspect queue position; for running jobs, compare the lack of progress with the node's expected work; for terminal failures, read details and server logs. Use [troubleshooting.md](troubleshooting.md) for model/backend failures and successful-looking corrupt images.

If operating specifically inside the local `comfy-agent`, respect its exposed path/host permission tools and user-approval channel. A recorded request does not grant access, and chat consent does not replace that application's technical approval mechanism. Its sandbox rules are application-specific, not rules for every coding agent.
