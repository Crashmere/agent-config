# Pricing notes

Read this reference before modifying the helper's rates, using another model, or interpreting incomplete usage. Prices are snapshots, not permanent facts.

## Current `gpt-image-2` snapshot

Verified against the official OpenAI [pricing page](https://developers.openai.com/api/docs/pricing#image-generation) and [image generation guide](https://developers.openai.com/api/docs/guides/image-generation#calculating-costs) on 2026-08-26.

- Token prices per one million tokens: text input `$5.00`, cached text input `$1.25`, image input `$8.00`, cached image input `$2.00`, and image output `$30.00`.
- Published output-only prices per image:

| Quality | 1024x1024 | 1024x1536 | 1536x1024 |
| --- | ---: | ---: | ---: |
| Low | $0.006 | $0.005 | $0.005 |
| Medium | $0.053 | $0.041 | $0.041 |
| High | $0.211 | $0.165 | $0.165 |

The non-square prices being lower than square prices are intentional for `gpt-image-2`; output token counts do not scale monotonically with pixel area. The helper uses this table only for the three listed sizes and multiplies it by `--n`.

## Exactness policy

- Report `exact` only when the response contains modality-separated total input usage, cached-input usage, and output usage sufficient to price the full request.
- Report `partial` when output usage can be priced but complete input or cache usage cannot. Do not assume that all input tokens are uncached.
- Report `estimate` when the helper falls back to the published output-only table. Input text and edit-image tokens remain excluded.
- Report `unknown` for unsupported models, automatic quality, non-table sizes without usable usage, or any case lacking an applicable rate.
- Never reuse this snapshot for a different model. Check current official documentation and update the model-specific logic first.

## Maintenance

When official prices or API usage fields change, update the constants, this dated snapshot, and focused synthetic tests together. Do not make a paid request solely to refresh pricing metadata.
