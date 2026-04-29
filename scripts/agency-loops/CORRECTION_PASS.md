# Correction Pass For All Agency Loops

Your next iteration is not a normal expansion pass. It is a schema-correction pass.

Read `VERIFIED_SCHEMA.md` before editing `research-brief.md`.

## Required Output Changes

1. Add a line near the top:

   `Current executable status: RUNNABLE_NOW | RUNNABLE_WITH_EXTRA_MATERIALIZATION | NEEDS_EXTERNAL_DATA | RESEARCH_ONLY`

2. Audit every `schema.table.column` reference.

   If the table or column is not in `VERIFIED_SCHEMA.md`, replace it with the real equivalent or mark it as `[GAP]`.

3. Remove or correct these non-existent references:

   - `fed.vw_agreement_current`
   - `fed.vw_agreement_originals`
   - `cra.t3010`
   - `cra.t3010_schedule6`
   - `general.entity_source_links.source_id`
   - `general.entity_source_links.source_row_id`
   - `cra.loop_universe.risk_score`
   - `dept_number_en`

4. Add one executable SQL sketch that uses only verified tables and columns, or explicitly state why the challenge cannot be executed from the current data.

5. Add one presentation sentence:

   `Presentation sentence: ...`

6. Preserve the six-section structure from `STRUCTURE.md`.

## Challenge-Specific Corrections

### 01 Zombie Recipients

Use `cra.govt_funding_by_charity` for government-funding share. Use `cra.cra_identification` for filing-year presence. Use `general.vw_entity_funding` for funding exposure across CRA/FED/AB.

Do not claim legal dissolution from the current schema. Current schema supports `stopped filing` or `stale filing` only. Legal dissolution, bankruptcy, revocation date, and revocation reason are external data gaps.

### 02 Ghost Capacity

Use `cra.govt_funding_by_charity`, `cra.overhead_by_charity`, and `cra.cra_compensation`.

Do not treat hospitals, school boards, or public health authorities as ghost-capacity leads without an exclusion/caveat. The naive query surfaces many legitimate public-service institutions.

Use language like `thin delivery-capacity signal` or `capacity-accounting anomaly`, not shell entity.

### 03 Funding Loops

Use `cra.loop_universe.score`, not `risk_score`.

Credit GovAlta for the precomputed loop universe. The agent's value is packaging, filtering, caveating denominational/federated structures, and turning loop metrics into action.

### 04 Sole Source And Amendment Creep

Federal current/original values must be computed from `fed.grants_contributions` with CTEs. Do not cite non-existent current/original views.

Alberta sole-source fields are in `ab.ab_sole_source`: `vendor`, `amount`, `ministry`, `contract_services`, `permitted_situations`, `start_date`, `end_date`, `display_fiscal_year`, `contract_number`.

### 05 Vendor Concentration

Federal categories should use `owner_org_title` and `prog_name_en`. Vendor/recipient identity should use `recipient_business_number` when present, otherwise `recipient_legal_name`.

Alberta sole-source concentration can use `ab.ab_sole_source.ministry`, `vendor`, and `amount`.

Distinguish procurement concentration from program design where a statutory transfer is intentionally one-recipient.

### 06 Related Parties

Use `cra.cra_directors` plus `general.vw_entity_funding` and/or `general.entity_golden_records`.

Name-only director overlaps are review leads only. They need identity validation. Do not claim one person controls entities unless the evidence includes a durable identifier or manual confirmation.

### 07 Policy Misalignment

This is `NEEDS_EXTERNAL_DATA` unless a policy text corpus is ingested.

Funding data exists in `fed.grants_contributions`, `ab.ab_grants`, `ab.ab_contracts`, `ab.ab_sole_source`, and `general.vw_entity_funding`, but policy commitments are not in the inspected schema.

### 08 Duplicative Funding And Gaps

Use `general.vw_entity_funding` for cross-jurisdiction funding overlap.

Do not call overlap a duplicate unless purpose, period, and eligible-cost categories are compared. Use `prog_name_en`, `prog_purpose_en`, `description_en`, `agreement_start_date`, `agreement_end_date`, `ab.ab_grants.program`, `ab.ab_grants.payment_date`, and `ab.ab_grants.fiscal_year` for a stronger purpose/period check.

Funding gaps require an external policy/priorities corpus.

### 09 Contract Intelligence

Current data can support spend-over-time, category/program growth, and concentration-over-time.

It does not support true unit-cost unless units, quantities, or deliverable counts are extracted from descriptions or external procurement documents.

Use `fed.grants_contributions.agreement_start_date`, `agreement_value`, `owner_org_title`, `prog_name_en`, `recipient_legal_name`; use `ab.ab_sole_source.start_date`, `display_fiscal_year`, `amount`, `vendor`, `ministry`, `contract_services`.

### 10 Adverse Media

This is `NEEDS_EXTERNAL_DATA`.

Do not invent a worked example with fake entity IDs, fake ref numbers, or fake adverse events. Use placeholders only when clearly marked, or cite a real external source.

The internal join target is `general.entity_golden_records` and `general.vw_entity_funding`. External data must provide regulator/court/source URL, event date, adverse category, entity name, and ideally BN or corporate identifier.

## Done Standard For The Correction Pass

The brief is improved when a reviewer can answer:

- Which parts are executable now?
- Which exact table/column supports each executable part?
- Which parts need external data?
- What SQL would the agent run?
- What would disprove the finding?
- What sentence can we safely say on stage?
