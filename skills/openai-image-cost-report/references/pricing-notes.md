# Pricing Notes

Use these pricing notes when reporting the cost of `gpt-image-2` image jobs.

## Current assumptions

- Prefer `gpt-image-2`.
- Prefer standard sizes with published output-image prices:
  - `1024x1024`
  - `1024x1536`
  - `1536x1024`
- Standard output-image prices used by the helper script:
  - `low`: `1024x1024=$0.006`, `1024x1536=$0.005`, `1536x1024=$0.005`
  - `medium`: `1024x1024=$0.053`, `1024x1536=$0.041`, `1536x1024=$0.041`
  - `high`: `1024x1024=$0.211`, `1024x1536=$0.165`, `1536x1024=$0.165`

## Exactness policy

- If the API response includes modality-separated usage details, compute and report the exact total.
- If the API response includes only output token usage, report the exact output cost and mark the result as `partial`.
- If the response lacks usable usage details, fall back to the published output-image price table and mark the result as `estimate`.

## User-facing language

Use `exact` only when the total request cost is fully derived from returned usage.

Use `partial` when only part of the bill is confirmed, for example the output-image portion.

Use `estimate` when the number comes from the published `gpt-image-2` output table rather than request-specific usage details.
