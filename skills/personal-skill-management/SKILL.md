---
name: personal-skill-management
description: Organize agent instructions and create, review, restructure, document, deploy, and continuously improve the user's personal skills in Crashmere/agent-config. Use when deciding whether behavior belongs in AGENTS.md or a skill, resolving overlapping responsibilities, maintaining the personal skill repository, investigating a missing required skill, or correcting a personal skill or bundled script after real use exposes a problem.
---

# Personal Skill Management

Treat `https://github.com/Crashmere/agent-config` as the source-controlled home for the user's global `AGENTS.md` and personally maintained skills. Reconstruct durable context from this skill and the repository rather than relying on previous conversations.

## Repository contract

- Use `~/agent-config` as the expected checkout when it exists; otherwise locate or clone `Crashmere/agent-config`.
- Store personal skills at `skills/<skill-name>/` and treat those directories as the source of truth.
- Keep the repository limited to the user's instructions and skills. Exclude credentials, runtime state, caches, third-party installed copies, and speculative management files.
- Keep `README.md` in Chinese with a concise inventory linking each skill directly to its `SKILL.md`.
- Preserve unrelated files and user changes.

## Decide ownership before editing

1. Read the relevant instruction file and briefly scan the names and descriptions of existing repository and available skills. Read full bodies only for the few likely to overlap.
2. Put always-on behavior, safety boundaries, broad workflow preferences, and stable environment constraints in `AGENTS.md`. Put project-specific guidance in the project layer.
3. Extend an existing skill when the behavior belongs to its primary responsibility. Reference an existing skill when it already owns a reusable capability. Create a new skill only for a distinct trigger and responsibility.
4. Keep each skill's primary responsibility explicit. Name cross-skill dependencies when they affect invocation or execution, and do not duplicate commands, workflows, or policy maintained elsewhere.
5. Merge overlapping guidance and remove obsolete wording. If a genuine conflict cannot be resolved from context, ask the user.
6. Explain the placement and reuse decision briefly before material structural changes.

## Create or restructure a skill

1. Use `skill-creator` for every new skill and substantial restructuring. Initialize new skills under `~/agent-config/skills`.
2. Use a lowercase hyphenated folder name matching the frontmatter `name`. Put purpose and triggering conditions in `description`; keep operational guidance in imperative form.
3. Include `agents/openai.yaml`. Add other resources only when they provide reusable value, and remove placeholders and unused files.
4. Apply progressive disclosure:
   - keep core decisions, primary workflow, resource navigation, and safety boundaries in `SKILL.md`;
   - move infrequent, platform-specific, provider-specific, advanced, or narrow procedures to directly referenced files under `references/`;
   - move repeated deterministic operations to `scripts/` and output-only material to `assets/`;
   - state when optional resources should be read or run, avoid deep reference chains, and do not split short content without a material context benefit.
5. Add only a concise routing or safety rule to `AGENTS.md` when always-on guidance is necessary; never duplicate the full skill there.

## Complete the applicable workflow

- Read [references/repository-workflow.md](references/repository-workflow.md) when updating README, validating changes, synchronizing client links, committing, pushing, or reporting repository work. Run `scripts/sync-skill-links.sh` from that workflow instead of recreating client links manually.
- Read [references/maintenance.md](references/maintenance.md) when a personal skill or bundled script fails in real use, or when a required skill cannot be found or loaded.

## Boundaries

- Manage only skills owned by the user here. Leave system, plugin-provided, installer-managed, and third-party skills outside the repository unless the user explicitly forks one.
- Do not broaden rules beyond the requested scope or treat product-specific loading behavior as universal.
- Do not claim that a skill contains the original conversation; preserve only durable decisions and workflows.
