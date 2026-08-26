---
name: personal-skill-management
description: Organize agent instructions and create, update, validate, deploy, document, and continuously improve the user's personally maintained skills in the Crashmere/agent-config GitHub repository. Use when adding, reviewing, simplifying, or reorganizing AGENTS.md files; deciding whether behavior belongs in AGENTS.md or a skill; resolving duplicate or conflicting instructions; creating, extracting, renaming, or maintaining a personal skill; investigating a required skill that cannot be found or loaded; correcting a skill or bundled script after its workflow or command fails in real use; updating the repository inventory; or keeping local agent clients and the repository synchronized.
---

# Personal Skill Management

Maintain the user's personal skills as source-controlled assets in the private GitHub repository `https://github.com/Crashmere/agent-config`. Do not rely on previous chat history; reconstruct the required context from this skill and the repository contents.

## Repository contract

- Use `~/agent-config` as the expected local checkout when it exists. Otherwise locate or clone `Crashmere/agent-config` before editing.
- Store every personally maintained skill at `skills/<skill-name>/`. Treat that directory as the source of truth.
- Keep the repository focused on the user's own `AGENTS.md` and skills. Do not add bootstrap scripts, doctor scripts, external-skill manifests, runtime state, credentials, caches, or third-party installed skill copies.
- Keep `README.md` in Chinese. Maintain its concise `现有内容` list, with each skill name linked directly to `./skills/<skill-name>/SKILL.md` and followed by one brief description.
- Preserve unrelated files and existing user changes.

## Instruction placement

1. Read the complete existing instruction file and relevant skills before editing. Respect higher-priority instructions and repository conventions.
2. Classify the requested behavior:
   - Keep always-on behavior, safety boundaries, broad workflow preferences, and stable environment constraints in `AGENTS.md`.
   - Put specialized workflows, domain knowledge, tool integrations, templates, and conditionally relevant procedures in a skill.
   - Keep project-specific guidance in the project's instruction layer rather than the global file.
3. Integrate new guidance with nearby rules. Merge overlaps and remove obsolete wording instead of appending disconnected instructions.
4. Preserve the user's intent while keeping always-loaded instructions concise and actionable.
5. If a requested rule genuinely conflicts with an existing rule and the intended priority cannot be inferred safely, stop and ask the user to resolve it.

## Workflow

1. Inspect repository status, current `AGENTS.md`, `README.md`, existing skills, and relevant links before editing. Pull with fast-forward only when the local branch is clean and behind its remote.
2. Before adding content or creating a skill, briefly scan the names and descriptions of existing repository skills and other available skills. Read the full body only for the few skills whose purpose may overlap.
3. Choose the smallest coherent ownership model:
   - extend an existing skill when the new behavior belongs to its primary responsibility;
   - reference an existing skill when it already owns a reusable capability, adding only the integration or specialization needed by the current skill;
   - create a new skill only when the behavior has a distinct trigger and responsibility;
   - avoid duplicating commands, workflows, or policy already maintained elsewhere.
4. Keep skill boundaries explicit. Each skill should have one clear primary responsibility, with cross-skill dependencies named in its description or body when they affect invocation or execution.
5. Apply the instruction-placement rules above to decide whether the requested behavior belongs in a skill and whether `AGENTS.md` needs a short always-on boundary or routing rule.
6. Explain the placement and reuse decision briefly before making material structural changes.
7. Use the available `skill-creator` for every new skill and for substantial skill restructuring. Initialize new skills directly under `~/agent-config/skills`.
8. Write the smallest complete skill:
   - use a lowercase hyphenated folder name matching the frontmatter `name`;
   - put triggering contexts in the frontmatter `description`;
   - keep operational instructions in imperative form;
   - include `agents/openai.yaml`;
   - add `scripts/`, `references/`, or `assets/` only when they provide real reusable value;
   - remove all generated placeholders and unused files.
9. Organize content for progressive disclosure so less important or more specialized material consumes context only when needed:
   - keep the `description` limited to purpose and triggering conditions because it is always visible to the runtime;
   - keep `SKILL.md` focused on the core decision logic, primary workflow, navigation, and safety boundaries needed whenever the skill triggers;
   - move infrequent, platform-specific, provider-specific, advanced, or narrowly scoped procedures into directly referenced files under `references/`;
   - move repeated deterministic operations into `scripts/`, and output-only templates or media into `assets/`;
   - state clearly in `SKILL.md` when each optional resource should be read or run, and avoid deep reference chains;
   - do not split short content merely to create more files; lower a section only when doing so materially reduces routine context without obscuring the main workflow.
10. Update `README.md` in the same change whenever a skill is added, renamed, removed, or materially changes purpose. Keep entries ordered consistently with the existing list.
11. If stable routing is needed, add only a concise routing or safety rule to `AGENTS.md`; do not duplicate the full skill workflow there.
12. Validate only the changed skill and the behavior directly affected by the change. Prefer the smallest risk-proportionate checks, such as the `skill-creator` validator, a focused script invocation, `git diff --check`, and targeted scans for placeholders or secrets. Expand validation only when shared infrastructure, cross-skill behavior, or a high-risk change justifies it. Do not rerun unrelated end-to-end workflows by default.
13. Make the repository-owned skill discoverable in the user's active agent clients by following the existing local linking pattern. Before creating a link, verify that the target is absent or already points to the repository; never overwrite an unrelated target. At minimum, verify Trae and Codex can resolve `SKILL.md`.
14. Review the final diff, commit a focused change, and push the current branch to the configured GitHub remote when the user's request includes completing or maintaining this repository. Verify that local HEAD and the remote branch match.
15. Report the skill path, documentation and routing changes, validation result, commit hash, push result, and any action the user still needs to take.

## Continuous maintenance

When a repository-owned skill or one of its bundled scripts is incomplete, incorrect, outdated, or fails during real use:

1. Complete the user's immediate task with a verified solution when possible; do not stop at a workaround without understanding why the documented workflow failed.
2. Compare the failure and working solution with the current skill instructions, commands, scripts, assumptions, and trigger description.
3. Decide whether the issue is a reusable defect in the skill or a one-off environmental condition. Update the repository only when the correction generalizes or the environment-specific condition needs to be documented.
4. Make the smallest appropriate correction. Update related scripts, metadata, routing, and the README description only when their behavior or purpose changed.
5. Re-run only the corrected command or smallest affected workflow when safe, then validate the changed skill or script and inspect the diff. Do not repeat an entire expensive workflow unless the change affects it broadly or focused validation cannot establish confidence.
6. Report both the original cause and the durable repository correction.

## Missing skills

If a required or explicitly referenced skill cannot be found or loaded:

1. Stop the workflow that depends on the missing skill. Do not silently replace its instructions with an improvised process or continue with destructive or state-changing actions.
2. Perform a quick, read-only source check using the skill name and surrounding context:
   - inspect the skills currently exposed by the runtime;
   - check this repository for a personally maintained skill;
   - check the expected user, project, system, and plugin skill locations that are relevant to the active client;
   - inspect lockfiles, plugin metadata, repository documentation, or known upstream sources when they can identify the installer or owner.
3. Do not perform a broad filesystem or network search when the likely locations and metadata are sufficient.
4. Report the missing skill, where it was expected, which likely sources were checked, the most likely source or cause, and what is required to restore it.
5. Wait for the user's direction before installing, relinking, replacing, or removing anything. Resume the original workflow only after the required skill is available or the user explicitly authorizes an alternative.

## Boundaries

- Manage only skills owned by the user in this repository. Leave installer-managed, plugin-provided, system, and third-party skills outside it unless the user explicitly chooses to fork one.
- Do not overwrite unrelated instructions, broaden a rule beyond the user's requested scope, or treat product-specific loading behavior as universal.
- Do not install missing dependencies, recreate unavailable environments, or introduce repository changes solely to run optional broad validation. Use an available focused check and disclose any meaningful unverified area instead.
- Never commit secrets, API keys, authentication material, sessions, memories, logs, databases, plugin caches, or machine-specific runtime state.
- Do not add repository-management files merely for hypothetical future use. Add only files required by the current skill and the concise README inventory.
- Do not claim that a skill contains the original conversation. It preserves the durable decisions and workflow needed by a future AI; transient conversation context remains outside the repository.
