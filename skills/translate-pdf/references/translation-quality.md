# Translation and review guide

Read before translating technical or long documents. Apply the translation contract in SKILL.md; use the checks below to make review concrete.

## Context and terminology

Maintain a small, task-local glossary rather than a universal substitution dictionary:

| Field | Purpose |
|---|---|
| Source term | Identify the expression, including a multiword term where needed. |
| Context | Distinguish the field, sense, or document-specific definition. |
| Target wording | Keep this concept consistent across batches. |
| Retained form | Record the original-language term or abbreviation needed for a figure or technical reference. |

Resolve a repeated word anew when its context changes. For example, agent can refer to software, a person, or a biological agent; worker can mean a person or a compute process; report can mean a document or a platform complaint; views can mean opinions or page views. Enforcement in a platform-policy passage need not mean law enforcement.

Use source definitions over habitual translations. If a document defines dual use as beneficial versus harmful use, do not narrow it to military versus civilian use. Preserve proper names and technical identifiers. Do not translate product names using their everyday dictionary meaning.

For each figure discussed in the prose, record the relevant visible label, the corresponding source phrase, and the translated occurrence retaining that label. Similar meanings may use different words in the caption and image. Inspect the actual image rather than assuming an English parenthesis in its title covers the figure's terminology. Keep this check task-local and omit labels that the prose does not discuss.

## Pass 1: compare with the source

For every unit, inspect the source, translation, and necessary context together:

- **Coverage:** does each claim, qualification, list item, example, note, and exception survive? Was anything inferred or added?
- **Roles and actions:** who performs the action, what is affected, and in which direction? Distinguish entering a system from exporting data, granting access from using access, and collecting records from deleting them.
- **Relations:** verify pronouns, parallel lists, modifier attachment, conditions, time, cause, and comparisons. Read across page and batch boundaries.
- **Evidence:** preserve possibility, suspicion, estimates, observations, attribution, and explicit uncertainty. Distinguish an author's assessment from a verified fact.
- **Numbers:** check value, range, unit, denominator, date, currency, and what is being counted. Localize numeric notation only when its value and meaning remain exact.
- **Terms:** check domain meaning, consistent concepts, abbreviations, and figure labels; never accept a fluent sentence that changes the underlying mechanism.

Examples illustrate error classes, not mandatory wording:

| Source | Wrong interpretation | Meaning to preserve |
|---|---|---|
| a fleet of EC2 workers | A team of employees | Compute workers or nodes |
| one million artificial views | A million opinions | Artificially generated viewing activity |
| scraped an existing list | Deleted a list | Collected data from the list |
| could support the activity | Supported it as an established fact | A possible supporting use |
| written in the register of a government report | Written in a registry | Government-report language or style |

If an error recurs, search for the source term and inspect each occurrence with context. Do not replace all matching target words blindly.

## Pass 2: read only the target prose

Read each batch continuously before looking back at the source. Check whether a reader can identify the participants, action, condition, and result without guessing the original wording. Repair literal idioms, missing objects, unclear antecedents, unnatural collocations, excessive passive constructions, and stacks of abstract nouns.

For Chinese, prefer explicit actions and familiar domain wording. For example, human in the loop normally describes continued human participation, not a person physically located inside a loop. Keep the author's register: do not convert a cautious report into promotional copy or a neutral description into an accusation.

Recheck every readability edit against the source. Natural wording may reorganize a sentence but must not invent explanatory facts. Retain unresolved source ambiguity and place necessary translator notes outside the body.

Pay special attention when clarifying compressed noun phrases or participles: do not turn commissioned work into a claim about the commissioned party, or add an intermediary organization or causal mechanism that the source does not establish. Preserve inferential wording such as suggests instead of silently making it categorical. A smoother revision can still introduce a semantic error.

## Batch and document completion

Track stable unit IDs and actual progress in a task-local manifest, for example:

    {"unit_id": "u0042", "semantic_review": "complete", "readability_review": "complete", "issues": []}

Use pending states until each pass is performed. The manifest is bookkeeping, not proof that a judgment is correct. Before delivery, check neighboring batches, repeated concepts, definitions, captions, and table references together; return any affected units to review when corrections change them.

Record batch scope and substantive findings as review proceeds. A generic review-method string or an unconditional completion flag is not evidence of a performed review. Unchanged draft text still needs source comparison. When comparing translation workflows, distinguish inherited correct text from new corrections and newly introduced problems; reuse percentages describe provenance, not quality or review effort.

For each unresolved issue, retain a source location, the problematic wording, and its consequence. Distinguish a clear meaning error from a defensible wording preference. Do not produce numerical quality scores or error rates without a defined sample and rubric.
