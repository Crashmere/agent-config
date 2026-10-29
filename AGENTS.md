# Global Agent Instructions

## Python environment policy

- Never install Python packages into the global environment unless the user explicitly requests it.
- Use the `python-environment` skill whenever Python execution requires third-party packages, environment creation or selection, dependency changes, or interpreter/package troubleshooting.

## Instruction management

- Write all skills in English, including `SKILL.md`, reference documents, agent metadata, template instructions, and script comments/help. Preserve exact non-English names, UI labels, quotations, matching literals, fixtures, and requested output content when translation would change their meaning or behavior. The skill's authoring language does not determine the user's response or deliverable language.
- Unless the user explicitly requests another language, write all agent-authored specification and maintenance documents in English. This includes `AGENTS.md`, project and server documentation, technical plans, operational runbooks, decision records, and handoff documents. Preserve exact source-language names, UI labels, quotations, matching literals, fixtures, and required user-facing content. This default does not determine the language of conversation, product copy, creative work, or other user-requested deliverables.
- Use the `personal-skill-management` skill when organizing agent instructions or creating and maintaining the user's own skills and their `agent-config` GitHub repository.
- Keep `~/agent-config/AGENTS.md` as the shared global instruction source. After maintaining it, synchronize client instruction links through the `personal-skill-management` workflow.
- When a personally maintained skill or its scripts prove incorrect during real use, fix the immediate task, then use `personal-skill-management` to reassess and update the skill so the repository remains accurate.
- If a required skill cannot be found or loaded, quickly investigate its likely source, pause the dependent workflow, and report the missing skill and findings to the user instead of silently substituting another process.
- Treat skill frontmatter descriptions as scarce, always-loaded routing metadata: keep each description to one concise sentence containing only the primary capability and distinctive trigger terms, and move feature inventories, procedures, exclusions, and delegation details into the skill body.
- When maintaining personal skills, keep descriptions normally at or below 160 characters and the active personal catalog at or below 2,400 description characters. Check TRAE's aggregate skill-metadata budget once only when a personal skill is added, removed, or renamed, or when frontmatter descriptions change; body, reference, script, and project-document edits do not trigger the probe. Shorten user-owned descriptions before considering supported disablement of genuinely unused skills or plugins, and never edit installed or cached third-party metadata to save space.

## Software installation policy

- Prefer official or first-party software sources.
- Use the `software-installation` skill for software installation, upgrade, removal, or installation troubleshooting.
- On macOS, assess each software removal individually: prefer a complete official uninstall process when available and use the `mole` skill as a supplement; otherwise use Mole when appropriate. Use Mole for storage cleanup, except for straightforward deletion of explicitly identified files or directories.
- When the user explicitly requests installation, complete it and verify the result unless a material risk or unresolved choice requires confirmation.

## General workflow

- Keep changes safe, scoped, and relevant to the task.
- Explain destructive actions and ask for confirmation before running them.

## Design principles

- Before adding a design, check whether existing components, interfaces, workflows, or data models can support it. When designs share a responsibility, consider consolidating them or extracting their common behavior.
- Balance reuse and generality against implementation, comprehension, and maintenance costs. Introduce abstractions when concrete shared needs justify them; keep their scope proportional to those needs. Explain the tradeoffs that materially affect the chosen design.

## Technical communication and documentation

Apply these rules to technical replies, design documents, code explanations, comments, and maintenance documentation.

- Organize the explanation around the reader's task and decisions. Introduce the outcome or key design early, then explain the causal relationships or data flow needed to understand it. Keep a coherent abstraction level within each passage and connect implementation details to the design they explain.
- Allocate detail according to its effect on understanding and decisions. Explain core logic, consequential tradeoffs, and constraints that affect correctness or use. Summarize routine parsing, format conversion, validation, and error handling unless they determine business semantics or whether the design works. Include a detail when omitting it could cause a material misunderstanding or a different implementation.
- Give each point one main place where it is explained. An overview may identify key decisions; later sections should add mechanisms, evidence, or implementation details. Refer back briefly when needed. Remove repeated importance claims, conclusions that merely restate a section, and transitions that only announce the next section.
- When revising a document, rewrite affected passages into a coherent account of the current design, state, and constraints. Remove superseded conclusions, abandoned branches, and conversation-dependent notes about what was previously discussed or what the document omits. Retain concise reasons that explain current choices to a new reader; preserve historical decisions in records whose purpose requires that history.
- State actual behavior, conditions, and consequences directly. For an apparently defensive sentence, ask who uses it, what understanding or decision it changes, and what becomes false or misleading if it is removed. Judge its role in context rather than banning particular words or all negative phrasing.
- Remove artificial contrasts without a concrete ambiguity, and sentences that only narrate diligence, apologize, anticipate imaginary criticism, or describe exclusions the reader does not need. Collapse stacked hedges into one qualifier matched to the evidence. Keep requested or meaning-changing limitations beside the claims they limit, and put editor-only verification notes in working notes. Moving an unnecessary disclaimer to a footnote does not make it useful.
- Explain value through specific mechanisms and evidence. Replace generic claims about stability, flexibility, performance, or importance with what a component does, when it does it, and the resulting benefit or cost. Remove evaluative language that adds no information. Comments should explain non-obvious reasons or constraints rather than restating adjacent code.
- Use familiar, precise words and explicit verbs. Keep the subjects, conditions, and connections needed for smooth reading; allow short sentences and natural phrasing while maintaining a serious, plain tone. Trim repetition and filler before compressing useful explanation. Use one consistent term for each concept throughout the document.
- Choose structure to fit the content. Use prose for reasoning, lists for genuinely parallel items, and tables for comparisons or mappings. Add headings, examples, code snippets, and diagrams when they clarify the explanation. Scale the structure to the problem rather than filling a fixed template or splitting continuous reasoning into many tiny sections.
- Distinguish existing behavior, proposed behavior, and consequential unknowns. Ground factual claims in code, configuration, interfaces, or reliable sources, and support performance figures, compatibility promises, and verification conclusions with evidence. State defined behavior plainly and attach uncertainty to the specific unresolved matter. When rewriting, preserve material facts, numbers, actors, attribution, scope, and evidence strength; do not turn uncertainty into certainty or correlation into causation.
- Review the complete requested artifact once, including captions, introductions, and delivery notes, to preserve meaning and prevent removed defenses from reappearing around the edited text. Return already direct, faithful text unchanged when no useful edit remains.

## Testing and investigation discipline

- Minimize unnecessary tests and test runs. Before adding or running a test, identify the concrete behavior or failure it would check, whether that situation can realistically occur, how likely it is, and whether detecting it justifies the effort. Skip tests without a meaningful answer.
- Do not add tests merely to increase coverage or demonstrate that testing happened. Avoid unit tests that mirror the implementation, trivial assertions, hash or snapshot comparisons without a real integrity requirement, and elaborate fixtures for impossible or extremely unlikely states.
- During normal development, treat sufficiently unlikely hypothetical failures as acceptable risk. Consider them briefly, then move on instead of spending time on speculative tests or deep investigation. Examine unusual conditions and implementation details thoroughly when an actual failure, reproducible symptom, or concrete evidence makes that investigation relevant.
- Prefer the smallest check that verifies the requested behavior, reusing existing checks when useful. Simple documentation, cosmetic, and other reversible low-impact changes do not automatically need tests. Ordinary UI changes do not default to a desktop-plus-mobile, keyboard, screenshot, and browser matrix; check only the affected interaction and any viewport or input mode whose behavior could realistically differ. Add regression tests only when they protect against a plausible recurrence of a real problem.
- Stop once the relevant checks pass. Expand or repeat testing only when new changes, failures, or unresolved concrete concerns justify it. Honor explicit test requests and mandatory project checks within their applicable scope.

## Web keyboard and focus policy

- For all web services developed or maintained for the user, block ordinary Tab and Shift+Tab from moving focus between page controls by default, including menus, forms, dialogs, and dynamically loaded pages. Change this only when the user explicitly requests a different behavior.
- Do not show control focus highlights: remove browser focus outlines and focus-only shadows, border/color changes, and similar decoration unless the user explicitly requests them. Keep text carets, text/content selections, and business selection states working.
- Preserve explicitly requested Tab shortcuts and document-editing commands such as indentation and table-cell navigation. Keep Ctrl/Command/Alt combinations and IME composition outside the default interception; do not disable controls, blur them, or prevent normal text input to hide focus.

## Personal servers and hosted projects

- In server-related replies and maintenance documents, explicitly identify the target as `ali`, `nas`, `vps`, or the applicable combination; do not leave the server unspecified.
- Use `server-operations` before working on the user's personal Linux servers (including SSH host `ali`), their hosted projects, or adding another deployment. Explicitly read remote `/opt/AGENTS.md`; SSH does not automatically load remote agent instructions.
- Keep shared server context in `agent-config/skills/server-operations` and project details in each project's `AGENTS.md` and `docs`. Update source configuration whenever its behavior changes. Update project operations docs or shared current-state docs only when a durable operational contract changes, such as runtime, data layout, backup or recovery, authentication or access, deployment, or shared architecture; routine visual fixes and release records do not trigger those documents. Remove obsolete descriptions and synchronize server copies only when managed documentation changed.
- For shared architecture changes, inspect the entire application inventory and update all affected projects.
- Follow the authorization table in `server-operations` SKILL.md. Documentation edits, commits, pushes and server doc syncs, cleanup of known junk, documented fixes, and fixes to your own mistakes are done without asking and reported afterward. Ask first only for the items that table lists, such as real data or backups, access or permission changes, other apps' downtime, and costs.
