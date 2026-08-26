---
name: openai-image-cost-report
description: Generate or edit images with the local OpenAI API key, using `gpt-image-2` by default, and report per-call cost information after each image job. Use when the user wants Codex to check local `OPENAI_API_KEY`, call the OpenAI Image API directly instead of the built-in image tool, save the generated image locally, and include a cost summary in the reply.
---

# OpenAI Image Cost Report

Use this skill when the user wants an OpenAI-API-based image workflow with explicit cost reporting. Prefer this skill over ad hoc shell commands so the key check, model selection, file output, and cost summary are handled consistently.

## Workflow

1. Verify `OPENAI_API_KEY` is available in the current shell before doing anything else.
2. Prefer `gpt-image-2` unless the user explicitly requests another GPT Image model.
3. Prefer the helper script at `scripts/openai_image_with_cost.py` for both generation and editing.
4. Save outputs into the current workspace or the path explicitly requested by the user.
5. After each successful image call, read the script's cost summary and include it in the reply.

## Key Handling

Check the environment variable from the active shell:

```powershell
if ($env:OPENAI_API_KEY) { "SET" } else { "MISSING" }
```

If missing, stop and ask the user to set it locally. Do not ask the user to paste the key into chat.

## Environment

If Python execution is needed, follow project-local environment rules:

1. Find the project root when working inside a repo.
2. Reuse a local `.venv` if present; otherwise create one with `uv venv .venv`.
3. Install only the minimum dependency needed for this workflow:

```powershell
uv pip install --python .venv\Scripts\python.exe openai
```

The helper script itself uses only the `openai` package plus the Python standard library.

## Default Choices

Prefer standard `gpt-image-2` sizes that have published per-image output prices, because they make cost reporting cleaner:

- `1024x1024` for square assets
- `1024x1536` for portrait assets
- `1536x1024` for landscape assets

Use `high` quality only when the user wants a final asset; use `medium` or `low` for drafts.

## Commands

Generate a new image:

```powershell
.venv\Scripts\python.exe C:\Users\Administrator\.codex\skills\openai-image-cost-report\scripts\openai_image_with_cost.py generate `
  --prompt "A pale blue babydoll dress product mockup" `
  --size 1024x1536 `
  --quality high `
  --out output\imagegen\dress.png
```

Edit one or more reference images:

```powershell
.venv\Scripts\python.exe C:\Users\Administrator\.codex\skills\openai-image-cost-report\scripts\openai_image_with_cost.py edit `
  --prompt "Change only the dress fabric and keep the model and scene unchanged." `
  --image 1.jpg `
  --image 2.jpg `
  --size 1024x1536 `
  --quality high `
  --out output\imagegen\dress-edit.png
```

Use `--dry-run` first when you want to preview the resolved request and the likely output-image price without making an API call.

## Cost Reporting Rules

Always include a short cost block in the user-facing reply after each successful call.

Preferred format:

```text
Model: gpt-image-2
Mode: generate|edit
Saved: <path>
Cost: $X.XXXX
Basis: exact|partial|estimate
```

Interpret the helper script's report as follows:

- `exact`: the API response exposed enough usage detail to compute the full request cost.
- `partial`: the script could confirm only part of the cost, usually the output-image cost.
- `estimate`: the script used the published per-image output table because the API response did not expose enough usage detail.

If the report is `partial` or `estimate`, say so explicitly instead of pretending the number is exact.

## References

Read `references/pricing-notes.md` when you need the current pricing assumptions or the rationale behind `exact` vs `estimate`.
