---
name: instruction-management
description: Organize and maintain global or project-level agent instructions and skills. Use when adding, updating, reviewing, simplifying, or reorganizing AGENTS.md files; deciding whether behavior belongs in AGENTS.md or a skill; resolving duplicate or conflicting instructions; or changing the structure of an agent configuration repository.
---

# Instruction Management

## Workflow

1. Read the complete existing instruction file and any relevant skills before editing. Respect higher-priority instructions and repository conventions.
2. Classify the requested behavior:
   - Keep always-on behavior, safety boundaries, broad workflow preferences, and stable environment constraints in `AGENTS.md`.
   - Put specialized workflows, domain knowledge, tool integrations, templates, and conditionally relevant procedures in a skill.
   - Keep project-specific guidance in the project's instruction layer rather than the global file.
3. Explain the placement decision briefly before making material structural changes.
4. Integrate new guidance with nearby rules. Merge overlaps and remove obsolete wording instead of appending disconnected instructions.
5. Preserve the user's intent while keeping always-loaded instructions concise and actionable.
6. If a requested rule genuinely conflicts with an existing rule and the intended priority cannot be inferred safely, stop and ask the user to resolve it.
7. Validate the resulting file structure, formatting, and effective loading behavior when the runtime provides a check.

## Skill changes

- Use the available `skill-creator` when creating or substantially restructuring a skill.
- Keep only triggering information in the skill description and procedural guidance in the body.
- Add scripts, references, or assets only when they provide reusable value.
- Do not duplicate the same instruction across `AGENTS.md` and a skill except for a short always-on safety boundary or routing rule.

## Guardrails

- Do not overwrite unrelated instructions or user-owned changes.
- Do not broaden a rule beyond the user's requested scope.
- Do not treat product-specific paths or loading behavior as universal; verify them with the relevant product guidance when necessary.
