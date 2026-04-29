# Loop 08 — Duplicative Funding (and Funding Gaps)

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Duplicative Funding (and Funding Gaps)**.

## The Challenge (verbatim)

> Which organizations are being funded by multiple levels of government for the same purpose, potentially without those governments knowing about each other? The flip side is equally important: where do all levels of government claim to prioritize something, yet none of them are actually funding it? Duplication catches waste. Gaps catch failure.

## Your Goal

Produce `research-brief.md` per `../STRUCTURE.md`. Jury-ready.

## Domain priors

- **The unlock**: `general.entity_golden_records` (~851K rows) already canonicalizes organizations across CRA + FED + AB via deterministic + Splink + LLM authoring. The columns `cra_profile`, `fed_profile`, `ab_profile` are JSONB summaries per jurisdiction. `dataset_sources` is an array `['cra', 'fed', 'ab']` when an entity appears in all three. `source_link_count` shows how many source rows resolved into the canonical entity (top entry is Salvation Army at 14,082 links).
- **Duplicative-funding query**: filter golden records where all three profiles are populated AND fed_total + ab_total exceed thresholds. We have a working version of this skill running in LemonClaw.
- **Same-purpose validation**: hardest. Two grants to the same org for "skills training" might be one initiative cofunded or two unrelated programs. Embedding similarity on `prog_name_en` (FED) + `program` (AB) is the proposed approach. Without that, it is a candidate, not a finding.
- **Funding-gaps side**: needs policy commitments (see Loop 07) plus zero-spend evidence. Inverse of Loop 07. The `[GAP]` here is the same as the Loop 07 `[GAP]`.
- **Quality issues**: F-7 (47K federal rows missing BN) means some entities will not link to golden records and will undercount duplication. C-3 (donee BN→name mismatches) means some CRA flows are unjoinable. The methodology must report unjoinable shares.

## Read first

- `../STRUCTURE.md`
- `../KNOWN-DATA-ISSUES-NOTES.md`
- `../../general/README.md` if available locally for entity-resolution methodology.

## Reminders

- Cite the GovAlta entity-resolution paper / README, since the golden records are the foundation of this challenge.
- Frame the duplication as "uncoordinated overlap" — the lens lets ministers act without it sounding accusatory.
- A worked example using a real top-link entity (Salvation Army, YMCA, Catholic Charities of Alberta, etc.) is required.

Begin.
