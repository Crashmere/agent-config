---
name: personal-skill-management
description: Create, update, validate, deploy, document, and version the user's personally maintained agent skills in the Crashmere/agent-config GitHub repository. Use whenever the user asks to create, extract, reorganize, rename, or maintain one of their own skills; add a personal workflow to their skill collection; update the repository skill inventory; or keep local agent clients and the agent-config repository synchronized.
---

# Personal Skill Management

Maintain the user's personal skills as source-controlled assets in the private GitHub repository `https://github.com/Crashmere/agent-config`. Do not rely on previous chat history; reconstruct the required context from this skill and the repository contents.

## Repository contract

- Use `~/agent-config` as the expected local checkout when it exists. Otherwise locate or clone `Crashmere/agent-config` before editing.
- Store every personally maintained skill at `skills/<skill-name>/`. Treat that directory as the source of truth.
- Keep the repository focused on the user's own `AGENTS.md` and skills. Do not add bootstrap scripts, doctor scripts, external-skill manifests, runtime state, credentials, caches, or third-party installed skill copies.
- Keep `README.md` in Chinese. Maintain its concise `现有内容` list, with each skill name linked directly to `./skills/<skill-name>/SKILL.md` and followed by one brief description.
- Preserve unrelated files and existing user changes.

## Workflow

1. Inspect repository status, current `AGENTS.md`, `README.md`, existing skills, and relevant links before editing. Pull with fast-forward only when the local branch is clean and behind its remote.
2. Use the available `instruction-management` skill to decide whether the requested behavior belongs in a skill and whether `AGENTS.md` needs a short always-on boundary or routing rule.
3. Use the available `skill-creator` for every new skill and for substantial skill restructuring. Initialize new skills directly under `~/agent-config/skills`.
4. Write the smallest complete skill:
   - use a lowercase hyphenated folder name matching the frontmatter `name`;
   - put triggering contexts in the frontmatter `description`;
   - keep operational instructions in imperative form;
   - include `agents/openai.yaml`;
   - add `scripts/`, `references/`, or `assets/` only when they provide real reusable value;
   - remove all generated placeholders and unused files.
5. Update `README.md` in the same change whenever a skill is added, renamed, removed, or materially changes purpose. Keep entries ordered consistently with the existing list.
6. If stable routing is needed, add only a concise routing or safety rule to `AGENTS.md`; do not duplicate the full skill workflow there.
7. Validate every changed skill with the validator supplied by `skill-creator`. If its Python dependencies are unavailable globally, run it in an isolated `uv` environment rather than installing globally. Run `git diff --check` and scan for leftover placeholders and obvious secrets.
8. Make the repository-owned skill discoverable in the user's active agent clients by following the existing local linking pattern. Before creating a link, verify that the target is absent or already points to the repository; never overwrite an unrelated target. At minimum, verify Trae and Codex can resolve `SKILL.md`.
9. Review the final diff, commit a focused change, and push the current branch to the configured GitHub remote when the user's request includes completing or maintaining this repository. Verify that local HEAD and the remote branch match.
10. Report the skill path, documentation and routing changes, validation result, commit hash, push result, and any action the user still needs to take.

## Boundaries

- Manage only skills owned by the user in this repository. Leave installer-managed, plugin-provided, system, and third-party skills outside it unless the user explicitly chooses to fork one.
- Never commit secrets, API keys, authentication material, sessions, memories, logs, databases, plugin caches, or machine-specific runtime state.
- Do not add repository-management files merely for hypothetical future use. Add only files required by the current skill and the concise README inventory.
- Do not claim that a skill contains the original conversation. It preserves the durable decisions and workflow needed by a future AI; transient conversation context remains outside the repository.
