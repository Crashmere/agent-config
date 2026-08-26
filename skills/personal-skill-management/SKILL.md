---
name: personal-skill-management
description: Organize agent instructions and create, update, validate, deploy, document, and version the user's personally maintained skills in the Crashmere/agent-config GitHub repository. Use when adding, reviewing, simplifying, or reorganizing AGENTS.md files; deciding whether behavior belongs in AGENTS.md or a skill; resolving duplicate or conflicting instructions; creating, extracting, renaming, or maintaining a personal skill; updating the repository inventory; or keeping local agent clients and the repository synchronized.
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
2. Apply the instruction-placement rules above to decide whether the requested behavior belongs in a skill and whether `AGENTS.md` needs a short always-on boundary or routing rule.
3. Explain the placement decision briefly before making material structural changes.
4. Use the available `skill-creator` for every new skill and for substantial skill restructuring. Initialize new skills directly under `~/agent-config/skills`.
5. Write the smallest complete skill:
   - use a lowercase hyphenated folder name matching the frontmatter `name`;
   - put triggering contexts in the frontmatter `description`;
   - keep operational instructions in imperative form;
   - include `agents/openai.yaml`;
   - add `scripts/`, `references/`, or `assets/` only when they provide real reusable value;
   - remove all generated placeholders and unused files.
6. Update `README.md` in the same change whenever a skill is added, renamed, removed, or materially changes purpose. Keep entries ordered consistently with the existing list.
7. If stable routing is needed, add only a concise routing or safety rule to `AGENTS.md`; do not duplicate the full skill workflow there.
8. Validate every changed skill with the validator supplied by `skill-creator`. If its Python dependencies are unavailable globally, run it in an isolated `uv` environment rather than installing globally. Run `git diff --check` and scan for leftover placeholders and obvious secrets.
9. Make the repository-owned skill discoverable in the user's active agent clients by following the existing local linking pattern. Before creating a link, verify that the target is absent or already points to the repository; never overwrite an unrelated target. At minimum, verify Trae and Codex can resolve `SKILL.md`.
10. Review the final diff, commit a focused change, and push the current branch to the configured GitHub remote when the user's request includes completing or maintaining this repository. Verify that local HEAD and the remote branch match.
11. Report the skill path, documentation and routing changes, validation result, commit hash, push result, and any action the user still needs to take.

## Boundaries

- Manage only skills owned by the user in this repository. Leave installer-managed, plugin-provided, system, and third-party skills outside it unless the user explicitly chooses to fork one.
- Do not overwrite unrelated instructions, broaden a rule beyond the user's requested scope, or treat product-specific loading behavior as universal.
- Never commit secrets, API keys, authentication material, sessions, memories, logs, databases, plugin caches, or machine-specific runtime state.
- Do not add repository-management files merely for hypothetical future use. Add only files required by the current skill and the concise README inventory.
- Do not claim that a skill contains the original conversation. It preserves the durable decisions and workflow needed by a future AI; transient conversation context remains outside the repository.
