# Repository workflow

Read this reference when a change requires repository documentation, validation, local client discovery, Git commits, or GitHub synchronization.

## Prepare and document

1. Inspect Git status, the current branch and remote, `AGENTS.md`, `README.md`, affected skills, and relevant local links. Pull with fast-forward only when the working tree is clean and the branch is behind its remote.
2. Update `README.md` when a skill is added, renamed, removed, or materially changes purpose. Keep the existing concise Chinese inventory, link each entry only to `./skills/<skill-name>/SKILL.md`, and do not list bundled references, scripts, tests, or metadata files.
3. Update nearby `AGENTS.md` wording only when a stable routing or safety boundary is required.

## Validate proportionately

1. Validate only changed skills and directly affected behavior. Prefer the smallest risk-proportionate combination of the `skill-creator` validator, focused script invocations, `git diff --check`, and targeted placeholder or secret scans.
2. Expand validation only for shared infrastructure, cross-skill behavior, high-risk changes, or when focused checks cannot establish confidence. Do not rerun unrelated end-to-end workflows by default.
3. Do not install missing dependencies, recreate unavailable environments, or change the repository solely for optional broad validation. Use an available focused check and disclose meaningful unverified areas.

## Check the shared skill-metadata budget

1. After adding a skill or changing several descriptions, measure every active personal frontmatter description, not only the edited files. Keep each description normally at or below 160 characters and their combined total at or below 2,400 characters.
2. Run `traecli debug prompt-input 'skill budget probe'` and inspect the rendered `### Available skills` catalog. Confirm that the edited descriptions are active, count the listed skills, and compare any suspected shortened description with its source; repository-only length checks do not prove that the full active catalog fits TRAE's shared budget.
3. When validating from a TUI log, use a fresh session and inspect its newest `traex_core_skills::render` entry. An already running session may retain the catalog loaded at startup, while the standalone debug command does not write its result to `traecli-tui.log`.
4. If truncation remains, preserve distinctive routing terms while shortening user-owned descriptions again. Consider `[[skills.config]]` with `enabled = false` only for genuinely unused or redundant capabilities, using a `name` or absolute `path` selector supported by the installed TRAE version.
5. Never edit installed system skills, plugin caches, installer-managed skills, or other third-party metadata for budget relief. If all skills remain listed and useful third-party sources dominate the remaining fixed budget, retain those capabilities and report the measured constraint instead of optimizing for a warning-free catalog.

## Make the skill discoverable

1. After adding, renaming, or removing a skill, run `scripts/sync-skill-links.sh` from the skill directory. Its default mode reports missing, conflicting, and stale links without changing them.
2. Review the report, then run `scripts/sync-skill-links.sh --apply` to create missing links for the supported clients. The script may create their `skills` directories, but never overwrites an existing path. Resolve conflicts explicitly and review stale links manually.
3. Re-run report-only mode and verify that at least Trae and Codex resolve the repository-owned `SKILL.md`.

## Commit and report

1. Review the final diff and preserve unrelated changes.
2. Commit a focused change and push the current branch when the request includes completing or maintaining this repository. Verify local HEAD and the remote branch match.
3. Report changed skill paths, documentation or routing updates, focused validation performed, meaningful unverified areas, commit hash, push result, and any remaining user action.
