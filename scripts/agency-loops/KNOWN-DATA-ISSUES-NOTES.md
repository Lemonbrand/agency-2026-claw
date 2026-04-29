# GovAlta KNOWN-DATA-ISSUES — abridged notes for the loops

Source: https://github.com/GovAlta/agency-26-hackathon/blob/main/KNOWN-DATA-ISSUES.md
Snapshot date in source: 2026-04-19.

## FED — `fed.grants_contributions`

- **F-1**: 41,046 `ref_number` collisions across distinct recipients. Use `(ref_number, recipient_business_number, legal_name)` as partition key.
- **F-2**: 25,853 duplicate `(ref_number, amendment_number)` pairs.
- **F-3 (critical)**: `agreement_value` is cumulative, not delta. Naive SUM = $921B; correct via `vw_agreement_current` = $816B (current commitment); originals via `vw_agreement_originals` = $533B. Naive overstates by ~$388B / 73%.
- **F-4**: 4,633 negative agreement_value rows (4,617 on amendments — used as termination markers).
- **F-5**: 11,510 zero-value rows.
- **F-6**: BN format polyglot — 9-char, 15-char, garbage placeholders ("-"). ~28,600 rows outside expected formats.
- **F-7**: 47,102 NFP/for-profit rows missing BN where one is expected.
- **F-8**: 187,866 (14.7%) rows missing `agreement_end_date` (TBS-mandatory).
- **F-9**: 947 rows where end_date < start_date.
- **F-10**: `agreement_number` is free text and frequently a program code (URU, RGPIN, etc.) shared across thousands of unrelated grants. **Never a join key.**
- **F-11**: 2,900 amendment rows decrease the agreement value (8% of compared amendments).

## CRA — `cra.*`

- **C-1**: 54,010 T3010 arithmetic impossibilities across 30,856 BNs (12.8% of filings). Surfaced in `cra.t3010_impossibilities`. Top rules: `PARTITION_4950` (24,960), `COMP_4880_EQ_390` (13,504), `IDENTITY_5100` (6,697).
- **C-2**: 1,075 plausibility-flagged filings (unit-error candidates). Surfaced in `cra.t3010_plausibility_flags`.
- **C-3**: $8.97B in qualified-donee gifts unjoinable due to BN→name mismatches. 127,725 problem rows: 67,631 NAME_MISMATCH + 24,151 UNREGISTERED_BN + 35,913 MALFORMED_BN.
- **C-4**: 109,996 NULL `donee_bn` rows (6.6% of `cra_qualified_donees`); 47,338 malformed.
- **C-6**: `cra_directors` NULL rates: at_arms_length 4.96%, start_date 10.05%, first_name 0.11%. end_date 75.8% NULL is expected (active directors).
- **C-7**: Historical legal names not preserved. Only 1.4% of BNs show any name variation across 2020-2024 — well-known rebrands erased.
- **C-8**: T3010 form revised in 2024 (v24 → v27). Some fields exist only pre-2024 or only post-2023. Filtering by column without year-awareness gives confusing zeros.
- **C-11**: 20,192 well-formed donee BNs not in `cra_identification` (legitimate non-charity qualified donees: municipalities, universities, First Nations councils, UN agencies, plus some revoked-pre-2020 entities).
- **C-12** (resolved): Johnson cycles output non-simple cycles (158 rows); fix landed 2026-04-19, current `cra.johnson_cycles` is 4,601 simple cycles.

## AB — `ab.*`

- **A-2**: `ab_grants.lottery` is text 'True'/'False' with no CHECK; format risk if upstream changes.
- **A-3**: `ab_sole_source.special` semantics undocumented by Alberta.
- **A-4**: `ab_sole_source.permitted_situations` letter codes (a–l, z) — Alberta does not publish a letter→number codebook. Positional inference exists but is not Alberta-confirmed.
- **A-6**: 50,381 negative `ab_grants.amount` rows summing to -$13.11B. Alberta convention: negatives are reversals, not errors. `COUNT(*)` overstates payments.
- **A-9**: 320,284 CSV-sourced rows (FY 2024-25 + 2025-26) have NULL lottery, lottery_fund, version, created_at, updated_at. `lottery` cannot be filtered on for FY ≥ 2023-24.
- **A-10**: 616 rows for FY 2024-25 + 2025-26 with `recipient IS NULL` totalling $24.95B — publisher rollups (AISH beneficiaries, per-physician FFS, child-care worker support). Recipient-level aggregates must filter or bucket these.
- **A-11**: Genuine cabinet reorganisations create distinct ministry names across years; cross-year analyses need `general/data/ministries-history.json` crosswalk.
- **A-13**: 5,557 excess exact-duplicate rows + 951 perfect-reversal pairs in FY 2024-25 + 2025-26. `COUNT(*)` is unreliable as a payment count.

## general — entity resolution

- `entity_golden_records` (~853K rows): canonical entity per real-world organization. JSONB profiles per jurisdiction (`cra_profile`, `fed_profile`, `ab_profile`). `dataset_sources` array names which jurisdictions touched the entity. `bn_root` + `bn_variants[]` + `aliases` jsonb. Use this as the cross-jurisdictional join target whenever possible.
- `entity_source_links` (~5.16M rows): the per-source-row evidence trail behind each canonical entity.
- Methodology: deterministic (BN + normalized name + trade-name extraction in CRA→FED→AB trust order) + Splink probabilistic + Claude LLM verdict and authoring. ~67K LLM-confirmed merges, ~65K RELATED cross-links.

## How to use these notes

When a loop's methodology touches a table or column with a known issue, the brief MUST acknowledge the relevant issue ID (e.g. "Apply F-3 mitigation: use `vw_agreement_current` not raw `agreement_value`") in the methodology and observability sections. Pretending the data is clean is worse than acknowledging the dirt.
