---
name: openai-image-cost-report
description: Generate or edit images through the OpenAI Image API with the user's local API key, save the results, and report the cost basis for every request. Use when the user explicitly wants direct OpenAI API image generation or editing, local output files, or per-call cost reporting instead of the built-in image tool.
---

# OpenAI Image Cost Report

Use the bundled script for reproducible Image API requests and cost reports. Default to `gpt-image-2` unless the user names another model.

## Workflow

1. Confirm the requested prompt, operation (`generate` or `edit`), output path, size, quality, and image count. Use `1024x1024`, `1024x1536`, or `1536x1024` unless the user needs another supported `gpt-image-2` resolution.
2. Use `python-environment` to select an isolated interpreter and provide the `openai` package. Do not install it globally or prescribe a platform-specific environment path here.
3. Run `scripts/openai_image_with_cost.py --help` when command options are needed. Use `--dry-run` to validate parameters and obtain an output-only estimate without an API key, the `openai` package, or an API call.
4. Before a live request, check that `OPENAI_API_KEY` exists without printing its value. If missing, stop and ask the user to set it locally; never ask them to paste it into chat.
5. Run the helper for the live request. Preserve the generated image files and adjacent JSON cost report. Do not expose the key or raw authentication material in commands, logs, or replies.
6. Report the model, operation, saved paths, displayed USD cost, and basis. Clearly label output-only or unavailable totals.

## Defaults and cost semantics

- Use `high` for final assets and `medium` or `low` for drafts when the user has not specified quality.
- Treat `exact` as a full request cost calculated from API-returned input and output usage.
- Treat `partial` as a request-specific output cost that excludes some inputs.
- Treat `estimate` as the published output-image price for the selected standard size, quality, and count; it excludes input text and edit-image tokens.
- Treat `unknown` as no supported calculation. Never apply `gpt-image-2` rates to another model.
- Read [references/pricing-notes.md](references/pricing-notes.md) before changing pricing logic, using non-default models, or interpreting incomplete usage. Verify current official OpenAI pricing when accuracy matters because rates can change.

## Boundaries

- Use the Image API for a direct one-request generation or edit workflow. Do not silently substitute the Responses API, whose total cost can also include the mainline model.
- Do not make a billable API call merely to validate the skill or helper. Use dry-run and synthetic usage data unless the user requested an image job.
- If the API succeeds but local saving or reporting fails, retain available response details, explain the failure, and correct the helper through `personal-skill-management`.
